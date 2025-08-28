import runpod
from runpod.serverless.utils import rp_upload
import os
import websocket
import base64
import json
import uuid
import logging
import urllib.request
import urllib.parse
import time
import binascii # Import for Base64 error handling
from model_downloader import ensure_models_ready


# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CUDA check and configuration
def check_cuda_availability():
    """Check CUDA availability and set environment variables."""
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("✅ CUDA is available and working")
            os.environ['CUDA_VISIBLE_DEVICES'] = '0'
            return True
        else:
            logger.error("❌ CUDA is not available")
            raise RuntimeError("CUDA is required but not available")
    except Exception as e:
        logger.error(f"❌ CUDA check failed: {e}")
        raise RuntimeError(f"CUDA initialization failed: {e}")

# Execute CUDA check
try:
    cuda_available = check_cuda_availability()
    if not cuda_available:
        raise RuntimeError("CUDA is not available")
except Exception as e:
    logger.error(f"Fatal error: {e}")
    logger.error("Exiting due to CUDA requirements not met")
    exit(1)



server_address = os.getenv('SERVER_ADDRESS', '127.0.0.1')
client_id = str(uuid.uuid4())
def save_data_if_base64(data_input, temp_dir, output_filename):
    """
    Check if input data is a Base64 string, and if so, save it as a file and return the path.
    If it's a regular path string, return it as is.
    """
    # If input is not a string, return as is
    if not isinstance(data_input, str):
        return data_input

    try:
        # Base64 strings will succeed when attempting to decode
        decoded_data = base64.b64decode(data_input)
        
        # Create directory if it doesn't exist
        os.makedirs(temp_dir, exist_ok=True)
        
        # If decoding succeeds, save as temporary file
        file_path = os.path.abspath(os.path.join(temp_dir, output_filename))
        with open(file_path, 'wb') as f: # Save in binary write mode ('wb')
            f.write(decoded_data)
        
        # Return the path of the saved file
        print(f"✅ Saved Base64 input to file '{file_path}'.")
        return file_path

    except (binascii.Error, ValueError):
        # If decoding fails, treat as regular path and return original value
        print(f"➡️ Treating '{data_input}' as file path.")
        return data_input
    
def queue_prompt(prompt):
    url = f"http://{server_address}:8188/prompt"
    logger.info(f"Queueing prompt to: {url}")
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(url, data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    url = f"http://{server_address}:8188/view"
    logger.info(f"Getting image from: {url}")
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"{url}?{url_values}") as response:
        return response.read()

def get_history(prompt_id):
    url = f"http://{server_address}:8188/history/{prompt_id}"
    logger.info(f"Getting history from: {url}")
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())

def get_videos(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_videos = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break
        else:
            continue

    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        videos_output = []
        # Handle both video files and images
        if 'gifs' in node_output:  # VHS_VideoCombine outputs to 'gifs'
            for video in node_output['gifs']:
                video_data = get_image(video['filename'], video['subfolder'], video['type'])
                # Upload video to storage and return URL
                if isinstance(video_data, bytes):
                    video_url = rp_upload.upload_file_to_bucket(
                        file_data=video_data,
                        file_name=video['filename']
                    )
                    videos_output.append(video_url)
        elif 'images' in node_output:  # Fallback for image outputs
            for image in node_output['images']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                if isinstance(image_data, bytes):
                    import base64
                    image_data = base64.b64encode(image_data).decode('utf-8')
                videos_output.append(image_data)
        output_videos[node_id] = videos_output

    return output_videos

def load_workflow(workflow_path):
    with open(workflow_path, 'r') as file:
        return json.load(file)

def handler(job):
    job_input = job.get("input", {})

    logger.info(f"Received job input: {job_input}")
    task_id = f"task_{uuid.uuid4()}"
    
    # Ensure all required models are downloaded before processing
    logger.info("🔍 Checking required models...")
    if not ensure_models_ready():
        return {"error": "Failed to download required models. Please try again."}
    logger.info("✅ All models are ready for processing")

    # Validate required inputs
    if "image_path" not in job_input:
        return {"error": "Missing required parameter: image_path"}
    if "prompt" not in job_input:
        return {"error": "Missing required parameter: prompt"}

    try:
        image_input = job_input["image_path"]
        # Use helper function to get image file path (Base64 or Path)
        if image_input == "/example_image.png":
            image_path = "example_image.png"  # Use relative path since file exists in project root
        else:
            image_path = save_data_if_base64(image_input, task_id, "input_image.jpg")
            
        # Validate image file exists
        if not os.path.exists(image_path):
            return {"error": f"Image file not found: {image_path}"}
            
    except Exception as e:
        logger.error(f"Error processing input image: {e}")
        return {"error": f"Failed to process input image: {str(e)}"}
    

    try:
        prompt = load_workflow("/new-workflow.json")
    except Exception as e:
        logger.error(f"Failed to load workflow: {e}")
        return {"error": f"Failed to load workflow file: {str(e)}"}

    try:
        # Set input image (Node 91: LoadImage)
        prompt["91"]["inputs"]["image"] = image_path
        
        # Set text prompts (Node 88: CLIPTextEncode for positive prompt)
        prompt["88"]["inputs"]["text"] = job_input["prompt"]
        # Node 86 contains the negative prompt - keeping as specified in workflow
        
        # Set video dimensions with validation (Node 89: WanImageToVideo)
        width = job_input.get("width", 480)
        height = job_input.get("height", 832)
        if not (64 <= width <= 2048 and 64 <= height <= 2048):
            return {"error": "Width and height must be between 64 and 2048 pixels"}
        
        prompt["89"]["inputs"]["width"] = width
        prompt["89"]["inputs"]["height"] = height
        
        # Set video length/frame count with validation (Node 89: WanImageToVideo)
        video_length = job_input.get("video_length", 81)
        if not (1 <= video_length <= 300):
            return {"error": "Video length must be between 1 and 300 frames"}
        prompt["89"]["inputs"]["length"] = video_length
        
        # Set frame rate for video output with validation (Node 62: VHS_VideoCombine)
        frame_rate = job_input.get("frame_rate", 32)
        if not (1 <= frame_rate <= 60):
            return {"error": "Frame rate must be between 1 and 60 FPS"}
        prompt["62"]["inputs"]["frame_rate"] = frame_rate
        
        # Set video format (Node 62: VHS_VideoCombine)
        video_format = job_input.get("video_format", "video/h264-mp4")
        allowed_formats = ["video/h264-mp4", "video/webm", "image/gif"]
        if video_format not in allowed_formats:
            return {"error": f"Video format must be one of: {allowed_formats}"}
        prompt["62"]["inputs"]["format"] = video_format
        
        # Set random seeds for sampling (Node 81 & 82: KSamplerAdvanced)
        seed = job_input.get("seed", 443409249464707)
        prompt["81"]["inputs"]["noise_seed"] = seed
        prompt["82"]["inputs"]["noise_seed"] = seed + 1
        
    except KeyError as e:
        logger.error(f"Missing workflow node: {e}")
        return {"error": f"Workflow configuration error - missing node: {str(e)}"}
    except Exception as e:
        logger.error(f"Error configuring workflow: {e}")
        return {"error": f"Failed to configure workflow: {str(e)}"}

    ws_url = f"ws://{server_address}:8188/ws?clientId={client_id}"
    logger.info(f"Connecting to WebSocket: {ws_url}")
    
    try:
        # First check if HTTP connection is possible
        http_url = f"http://{server_address}:8188/"
        logger.info(f"Checking HTTP connection to: {http_url}")
        
        # Check HTTP connection (maximum 1 minute)
        max_http_attempts = 180
        for http_attempt in range(max_http_attempts):
            try:
                import urllib.request
                response = urllib.request.urlopen(http_url, timeout=5)
                logger.info(f"HTTP connection successful (attempt {http_attempt+1})")
                break
            except Exception as e:
                logger.warning(f"HTTP connection failed (attempt {http_attempt+1}/{max_http_attempts}): {e}")
                if http_attempt == max_http_attempts - 1:
                    raise Exception("Cannot connect to ComfyUI server. Please check if the server is running.")
                time.sleep(1)
        
        ws = websocket.WebSocket()
        # WebSocket connection attempt (maximum 5 minutes)
        max_attempts = int(300/5)  # 5 minutes (attempt once per second)
        for attempt in range(max_attempts):
            import time
            try:
                ws.connect(ws_url)
                logger.info(f"WebSocket connection successful (attempt {attempt+1})")
                break
            except Exception as e:
                logger.warning(f"WebSocket connection failed (attempt {attempt+1}/{max_attempts}): {e}")
                if attempt == max_attempts - 1:
                    raise Exception("WebSocket connection timeout (5 minutes)")
                time.sleep(5)
        
        try:
            videos = get_videos(ws, prompt)
            logger.info(f"Videos retrieved: {videos}")
        except Exception as e:
            logger.error(f"Failed to retrieve videos: {e}")
            return {"error": f"Failed to process video: {str(e)}"}
        finally:
            ws.close()

        # Handle case when no videos are generated
        if not videos:
            return {"error": "Unable to generate video."}
        
        try:
            # Return video output (node 62 is VHS_VideoCombine)
            if "62" in videos and videos["62"]:
                return {"video_url": videos["62"][0]}
            
            # Check alternative outputs
            for node_id in videos:
                if videos[node_id]:
                    return {"video_url": videos[node_id][0]}
            
            return {"error": "Video not found."}
            
        except Exception as e:
            logger.error(f"Failed to process video output: {e}")
            return {"error": f"Failed to process video output: {str(e)}"}
            
    except Exception as e:
        logger.error(f"WebSocket connection failed: {e}")
        return {"error": f"Connection to processing server failed: {str(e)}"}

runpod.serverless.start({"handler": handler})