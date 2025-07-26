import hashlib
import time
import base64
import os
import aiohttp
from models.data_models import UniquenessFactors

class StabilityAI:
    """Stability AI integration for image generation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        
    def generate_custom_seed(self, uniqueness_factors: UniquenessFactors) -> int:
        """Generate custom seed based on personal data"""
        combined_data = (
            uniqueness_factors.location_hash +
            uniqueness_factors.timestamp_seed +
            uniqueness_factors.wallet_entropy +
            (uniqueness_factors.biometric_hash or "")
        )
        
        seed_hash = hashlib.sha256(combined_data.encode()).hexdigest()
        return int(seed_hash[:8], 16) % (2**31 - 1)
    
    async def generate_image(self, prompt: str, uniqueness_factors: UniquenessFactors) -> dict:
        """Generate image using Stability AI"""
        
        seed = self.generate_custom_seed(uniqueness_factors)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "text_prompts": [
                {
                    "text": prompt,
                    "weight": 1.0
                },
                {
                    "text": "blurry, low quality, distorted, watermark, text, signature",
                    "weight": -1.0
                }
            ],
            "cfg_scale": 7.5,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": 30,
            "seed": seed
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Stability AI API error: {response.status} - {error_text}")
                
                response_data = await response.json()
                
                # Save image to local storage
                image_data = response_data["artifacts"][0]["base64"]
                image_filename = f"nft_image_{int(time.time())}_{seed}.png"
                image_path = f"static/images/{image_filename}"
                
                # Ensure directory exists
                os.makedirs("static/images", exist_ok=True)
                
                # Save image
                with open(image_path, "wb") as f:
                    f.write(base64.b64decode(image_data))
                
                return {
                    "image_url": f"/static/images/{image_filename}",
                    "seed": seed,
                    "prompt": prompt,
                    "quality_score": 0.8,  # Mock quality score
                    "attempt": 1
                }