import os
import urllib.request
import logging
import hashlib
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelDownloader:
    """Handles on-demand model downloading for ComfyUI."""
    
    def __init__(self):
        self.models_config = {
            'unet': {
                'wan2.2_i2v_high_noise_14B_Q5_0.gguf': {
                    'url': 'https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF/resolve/main/HighNoise/Wan2.2-I2V-A14B-HighNoise-Q5_0.gguf?download=true',
                    'path': '/ComfyUI/models/unet/wan2.2_i2v_high_noise_14B_Q5_0.gguf'
                },
                'wan2.2_i2v_low_noise_14B_Q5_0.gguf': {
                    'url': 'https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF/resolve/main/LowNoise/Wan2.2-I2V-A14B-LowNoise-Q5_0.gguf?download=true',
                    'path': '/ComfyUI/models/unet/wan2.2_i2v_low_noise_14B_Q5_0.gguf'
                }
            },
            'vae': {
                'wan_2.1_vae.safetensors': {
                    'url': 'https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF/resolve/main/VAE/Wan2.1_VAE.safetensors?download=true',
                    'path': '/ComfyUI/models/vae/wan_2.1_vae.safetensors'
                }
            },
            'clip': {
                'umt5_xxl_fp8_e4m3fn_scaled.safetensors': {
                    'url': 'https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors',
                    'path': '/ComfyUI/models/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors'
                }
            },
            'loras': {
                'lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors': {
                    'url': 'https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors?download=true',
                    'path': '/ComfyUI/models/loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors'
                }
            }
        }
        
    def _download_file(self, url, filepath, chunk_size=8192):
        """Download a file from URL to filepath with progress logging."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            logger.info(f"Downloading {os.path.basename(filepath)}...")
            
            # Download with progress tracking
            with urllib.request.urlopen(url) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(filepath, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            logger.info(f"Progress: {progress:.1f}% ({downloaded}/{total_size} bytes)")
                        
            logger.info(f"✅ Successfully downloaded {os.path.basename(filepath)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to download {os.path.basename(filepath)}: {e}")
            # Clean up partial download
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
    
    def ensure_model_exists(self, model_type, model_name):
        """Ensure a specific model exists, download if necessary."""
        if model_type not in self.models_config:
            logger.error(f"Unknown model type: {model_type}")
            return False
            
        if model_name not in self.models_config[model_type]:
            logger.error(f"Unknown model name: {model_name} for type {model_type}")
            return False
            
        model_info = self.models_config[model_type][model_name]
        filepath = model_info['path']
        
        # Check if model already exists
        if os.path.exists(filepath):
            logger.info(f"✅ Model {model_name} already exists at {filepath}")
            return True
            
        # Download the model
        logger.info(f"📥 Model {model_name} not found, downloading...")
        return self._download_file(model_info['url'], filepath)
    
    def ensure_all_models(self):
        """Ensure all required models are available."""
        logger.info("🔍 Checking and downloading required models...")
        
        success = True
        for model_type, models in self.models_config.items():
            for model_name in models.keys():
                if not self.ensure_model_exists(model_type, model_name):
                    success = False
                    
        if success:
            logger.info("✅ All models are ready!")
        else:
            logger.error("❌ Some models failed to download")
            
        return success
    
    def get_model_path(self, model_type, model_name):
        """Get the local path for a model."""
        if model_type in self.models_config and model_name in self.models_config[model_type]:
            return self.models_config[model_type][model_name]['path']
        return None

# Global instance
model_downloader = ModelDownloader()

def ensure_models_ready():
    """Convenience function to ensure all models are ready."""
    return model_downloader.ensure_all_models()

if __name__ == "__main__":
    # Test the downloader
    ensure_models_ready()