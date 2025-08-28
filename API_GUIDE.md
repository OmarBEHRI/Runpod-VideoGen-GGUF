# WAN Image-to-Video API Guide

This API endpoint converts static images into animated videos using the WAN (Wan Image to Video) model with advanced frame interpolation.

## Endpoint Overview

The service processes input images and generates high-quality animated videos based on text prompts using a sophisticated ComfyUI workflow.

## Request Format

### Required Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|----------|
| `image_path` | string | Input image as Base64 encoded string OR file path | `"data:image/jpeg;base64,/9j/4AAQ..."` or `"/path/to/image.jpg"` |
| `prompt` | string | Text description for the animation | `"A woman walking through a forest"` |

### Optional Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `width` | integer | 480 | 64-2048 | Video width in pixels |
| `height` | integer | 832 | 64-2048 | Video height in pixels |
| `video_length` | integer | 81 | 1-300 | Number of frames to generate |
| `frame_rate` | integer | 32 | 1-60 | Output video frame rate (FPS) |
| `video_format` | string | "video/h264-mp4" | See formats | Output video format |
| `seed` | integer | 443409249464707 | Any integer | Random seed for reproducible results |

### Supported Video Formats
- `"video/h264-mp4"` (default)
- `"video/webm"`
- `"image/gif"`

## Request Examples

### Minimal Request
```json
{
  "input": {
    "image_path": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
    "prompt": "A person dancing in the rain"
  }
}
```

### Full Request with All Parameters
```json
{
  "input": {
    "image_path": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
    "prompt": "A woman gracefully walking through a mystical forest with sunlight filtering through the trees",
    "width": 640,
    "height": 480,
    "video_length": 120,
    "frame_rate": 24,
    "video_format": "video/h264-mp4",
    "seed": 12345
  }
}
```

### Using File Path (for local files)
```json
{
  "input": {
    "image_path": "/example_image.png",
    "prompt": "The character starts to smile and wave"
  }
}
```

## Response Format

### Success Response
```json
{
  "video_url": "https://storage.runpod.io/bucket/video_12345.mp4"
}
```

### Error Response
```json
{
  "error": "Error description here"
}
```

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `"Missing required parameter: image_path"` | No image provided | Include `image_path` in request |
| `"Missing required parameter: prompt"` | No prompt provided | Include `prompt` in request |
| `"Image file not found: [path]"` | Invalid file path | Check file exists or use Base64 |
| `"Width and height must be between 64 and 2048 pixels"` | Invalid dimensions | Use valid width/height range |
| `"Video length must be between 1 and 300 frames"` | Invalid frame count | Use valid video_length range |
| `"Frame rate must be between 1 and 60 FPS"` | Invalid FPS | Use valid frame_rate range |
| `"Video format must be one of: [formats]"` | Invalid format | Use supported video format |
| `"Connection to processing server failed"` | ComfyUI server down | Wait and retry, or contact support |
| `"Unable to generate video"` | Processing failed | Check input image quality and prompt |

## Image Input Guidelines

### Supported Formats
- JPEG/JPG
- PNG
- WebP
- BMP

### Recommendations
- **Resolution**: 512x512 to 1024x1024 pixels for best results
- **Quality**: High-quality images produce better animations
- **Content**: Clear subjects work better than complex scenes
- **File Size**: Base64 encoded images should be under 10MB

### Base64 Encoding
To convert an image to Base64:
```python
import base64

with open('image.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')
    base64_string = f"data:image/jpeg;base64,{image_data}"
```

## Prompt Guidelines

### Effective Prompts
- **Be specific**: "A woman walking slowly through a forest" vs "movement"
- **Include motion**: "dancing", "flowing", "swaying", "moving"
- **Describe direction**: "walking towards camera", "turning left"
- **Add atmosphere**: "in golden sunlight", "during a storm"

### Example Prompts
- `"A person's hair flowing gently in the wind"`
- `"Water rippling in a calm lake with reflections"`
- `"Leaves falling slowly from trees in autumn"`
- `"A cat stretching and yawning on a sunny windowsill"`
- `"Smoke rising gracefully from a campfire"`

## Technical Details

### Processing Pipeline
1. **Input Validation**: Checks parameters and image format
2. **Image Processing**: Loads and prepares input image
3. **Text Encoding**: Processes positive and negative prompts
4. **Video Generation**: Uses WAN I2V model for initial frames
5. **Frame Interpolation**: RIFE model doubles frame count
6. **Video Encoding**: Combines frames into final video format
7. **Upload**: Stores result and returns download URL

### Model Information
- **Base Model**: WAN 2.2 I2V (Image-to-Video)
- **Frame Interpolation**: RIFE 4.7
- **Text Encoder**: UMT5-XXL
- **VAE**: WAN 2.1 VAE
- **LoRA**: LightX2V distilled model

### Performance Notes
- **Processing Time**: 30-120 seconds depending on parameters
- **GPU Memory**: Requires ~12GB VRAM
- **Output Quality**: Higher resolution and longer videos take more time
- **Batch Processing**: Single image per request

## Rate Limits and Quotas

- Maximum concurrent requests: Depends on your RunPod configuration
- Maximum video length: 300 frames (~10 seconds at 30fps)
- Maximum resolution: 2048x2048 pixels
- File size limits: 10MB for Base64 images

## Troubleshooting

### Common Issues
1. **Slow Processing**: Reduce video_length or resolution
2. **Poor Quality**: Use higher resolution input images
3. **Connection Errors**: Check if ComfyUI server is running
4. **Memory Errors**: Reduce batch size or image resolution

### Debug Information
The service logs detailed information about:
- CUDA availability and GPU usage
- Image processing steps
- WebSocket connection status
- Model loading progress
- Error details with stack traces

## Support

For technical support or questions:
- Check the logs for detailed error messages
- Ensure all required models are downloaded
- Verify CUDA and GPU availability
- Test with smaller parameters first

---

*This API is powered by ComfyUI with WAN Image-to-Video models and runs on RunPod serverless infrastructure.*