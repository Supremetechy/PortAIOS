"""
AI Model Manager for AI-OS
Handles model loading, caching, and lifecycle management
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
import shutil


class ModelFramework(Enum):
    """Supported ML frameworks"""
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    JAX = "jax"
    ONNX = "onnx"
    HUGGINGFACE = "huggingface"
    SKLEARN = "sklearn"
    XGBOOST = "xgboost"
    KERAS = "keras"
    UNKNOWN = "unknown"


class ModelType(Enum):
    """Types of AI models"""
    LLM = "llm"  # Large Language Model
    VISION = "vision"  # Computer Vision
    AUDIO = "audio"  # Audio/Speech
    MULTIMODAL = "multimodal"
    TABULAR = "tabular"
    REINFORCEMENT = "reinforcement"
    GENERATIVE = "generative"
    CLASSIFIER = "classifier"
    REGRESSION = "regression"
    EMBEDDING = "embedding"
    UNKNOWN = "unknown"


class ModelStatus(Enum):
    """Model status"""
    AVAILABLE = "available"
    LOADING = "loading"
    LOADED = "loaded"
    CACHED = "cached"
    DOWNLOADING = "downloading"
    ERROR = "error"
    UNLOADED = "unloaded"


@dataclass
class ModelMetadata:
    """Model metadata"""
    model_id: str
    name: str
    framework: ModelFramework
    model_type: ModelType
    version: str
    size_gb: float
    parameters_millions: Optional[int] = None
    input_shape: Optional[Tuple] = None
    output_shape: Optional[Tuple] = None
    description: str = ""
    author: str = ""
    license: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'model_id': self.model_id,
            'name': self.name,
            'framework': self.framework.value,
            'model_type': self.model_type.value,
            'version': self.version,
            'size_gb': self.size_gb,
            'parameters_millions': self.parameters_millions,
            'description': self.description,
            'author': self.author,
            'license': self.license,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat()
        }


@dataclass
class LoadedModel:
    """Information about a loaded model"""
    metadata: ModelMetadata
    status: ModelStatus
    path: str
    memory_usage_gb: float = 0.0
    gpu_id: Optional[int] = None
    load_time_seconds: float = 0.0


class ModelCache:
    """Model caching system"""
    
    def __init__(self, cache_dir: str = "/aios/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_index_file = self.cache_dir / "cache_index.json"
        self.cache_index: Dict[str, Dict] = self._load_cache_index()
        self.max_cache_size_gb = 100.0  # Default max cache size
    
    def _load_cache_index(self) -> Dict[str, Dict]:
        """Load cache index from disk"""
        if self.cache_index_file.exists():
            try:
                with open(self.cache_index_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_cache_index(self):
        """Save cache index to disk"""
        try:
            with open(self.cache_index_file, 'w') as f:
                json.dump(self.cache_index, f, indent=2)
        except Exception as e:
            print(f"[CACHE] Warning: Could not save cache index: {e}")
    
    def get_cache_path(self, model_id: str) -> Path:
        """Get cache path for a model"""
        # Create hash of model_id for directory name
        hash_obj = hashlib.md5(model_id.encode())
        cache_subdir = hash_obj.hexdigest()[:16]
        return self.cache_dir / cache_subdir
    
    def is_cached(self, model_id: str) -> bool:
        """Check if model is cached"""
        return model_id in self.cache_index and self.get_cache_path(model_id).exists()
    
    def add_to_cache(self, model_id: str, metadata: ModelMetadata, source_path: str):
        """Add model to cache"""
        cache_path = self.get_cache_path(model_id)
        
        try:
            # Create cache directory
            cache_path.mkdir(parents=True, exist_ok=True)
            
            # Copy model files
            if os.path.isdir(source_path):
                shutil.copytree(source_path, cache_path / "model", dirs_exist_ok=True)
            else:
                target = cache_path / "model"
                try:
                    os.link(source_path, target)
                except Exception:
                    shutil.copy2(source_path, target)
            
            # Save metadata
            metadata_file = cache_path / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata.to_dict(), f, indent=2)
            
            # Update cache index
            self.cache_index[model_id] = {
                'cached_at': datetime.now().isoformat(),
                'size_gb': metadata.size_gb,
                'path': str(cache_path)
            }
            self._save_cache_index()
            
            print(f"[CACHE] ✓ Cached model: {model_id}")
            
            # Check cache size and evict if necessary
            self._evict_if_needed()
            
        except Exception as e:
            print(f"[CACHE] ✗ Failed to cache model: {e}")
    
    def remove_from_cache(self, model_id: str):
        """Remove model from cache"""
        if model_id in self.cache_index:
            cache_path = self.get_cache_path(model_id)
            
            try:
                if cache_path.exists():
                    shutil.rmtree(cache_path)
                
                del self.cache_index[model_id]
                self._save_cache_index()
                
                print(f"[CACHE] ✓ Removed from cache: {model_id}")
            except Exception as e:
                print(f"[CACHE] ✗ Failed to remove: {e}")
    
    def get_cache_size_gb(self) -> float:
        """Get total cache size in GB"""
        total_size = 0
        for model_id, info in self.cache_index.items():
            total_size += info.get('size_gb', 0)
        return total_size
    
    def _evict_if_needed(self):
        """Evict old models if cache is too large"""
        current_size = self.get_cache_size_gb()
        
        if current_size > self.max_cache_size_gb:
            print(f"[CACHE] Cache size ({current_size:.2f} GB) exceeds limit ({self.max_cache_size_gb:.2f} GB)")
            
            # Sort by cached_at (oldest first)
            sorted_models = sorted(
                self.cache_index.items(),
                key=lambda x: x[1].get('cached_at', '')
            )
            
            # Evict oldest models until under limit
            for model_id, _ in sorted_models:
                if current_size <= self.max_cache_size_gb * 0.8:  # 80% of limit
                    break
                
                size = self.cache_index[model_id].get('size_gb', 0)
                self.remove_from_cache(model_id)
                current_size -= size
    
    def clear_cache(self):
        """Clear entire cache"""
        try:
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_index = {}
            self._save_cache_index()
            print("[CACHE] ✓ Cache cleared")
        except Exception as e:
            print(f"[CACHE] ✗ Failed to clear cache: {e}")


class ModelManager:
    """Central model management system"""
    
    def __init__(self, model_dir: str = "/aios/models", cache_dir: str = "/aios/cache"):
        root = os.environ.get("AIOS_ROOT")
        if root:
            model_dir = f"{root}/models"
            cache_dir = f"{root}/cache"
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache = ModelCache(cache_dir)
        self.loaded_models: Dict[str, LoadedModel] = {}
        self.model_registry: Dict[str, ModelMetadata] = {}
        self.max_loaded_memory_gb: float = 32.0
        
        self._scan_models()
    
    def _scan_models(self):
        """Scan model directory for available models"""
        print("[MODEL] Scanning model directory...")
        
        try:
            for model_path in self.model_dir.iterdir():
                if model_path.is_dir():
                    metadata_file = model_path / "metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r') as f:
                                data = json.load(f)
                            
                            metadata = ModelMetadata(
                                model_id=data.get('model_id', model_path.name),
                                name=data.get('name', model_path.name),
                                framework=ModelFramework(data.get('framework', 'unknown')),
                                model_type=ModelType(data.get('model_type', 'unknown')),
                                version=data.get('version', '1.0'),
                                size_gb=data.get('size_gb', 0),
                                parameters_millions=data.get('parameters_millions'),
                                description=data.get('description', ''),
                                tags=data.get('tags', [])
                            )
                            
                            self.model_registry[metadata.model_id] = metadata
                            
                        except Exception as e:
                            print(f"[MODEL] Warning: Could not load metadata for {model_path.name}: {e}")
        except Exception as e:
            print(f"[MODEL] Warning: Could not scan models: {e}")
        
        print(f"[MODEL] Found {len(self.model_registry)} model(s)")
    
    def register_model(self, metadata: ModelMetadata, model_path: str) -> bool:
        """Register a new model"""
        print(f"[MODEL] Registering model: {metadata.name}")
        
        try:
            # Create model directory
            target_dir = self.model_dir / metadata.model_id
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy model files
            if os.path.isdir(model_path):
                shutil.copytree(model_path, target_dir / "files", dirs_exist_ok=True)
            else:
                shutil.copy2(model_path, target_dir / "files")
            
            # Save metadata
            metadata_file = target_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata.to_dict(), f, indent=2)
            
            # Add to registry
            self.model_registry[metadata.model_id] = metadata
            
            print(f"[MODEL] ✓ Registered: {metadata.name}")
            return True
            
        except Exception as e:
            print(f"[MODEL] ✗ Failed to register: {e}")
            return False
    
    def load_model(self, model_id: str, gpu_id: Optional[int] = None, available_memory_gb: Optional[float] = None) -> bool:
        """Load a model into memory"""
        if model_id in self.loaded_models:
            print(f"[MODEL] Model already loaded: {model_id}")
            return True
        
        if model_id not in self.model_registry:
            print(f"[MODEL] Model not found: {model_id}")
            return False
        
        metadata = self.model_registry[model_id]
        print(f"[MODEL] Loading model: {metadata.name}")
        
        try:
            if available_memory_gb is not None:
                required = self.estimate_memory_required(model_id)
                if required > available_memory_gb:
                    print(f"[MODEL] Insufficient memory to load {model_id}: {required:.2f} GB required")
                    return False

            self._evict_loaded_if_needed(metadata.size_gb)
            # Check if cached
            if self.cache.is_cached(model_id):
                model_path = str(self.cache.get_cache_path(model_id) / "model")
                print(f"[MODEL]   Using cached version")
            else:
                model_path = str(self.model_dir / model_id / "files")
                # Add to cache
                self.cache.add_to_cache(model_id, metadata, model_path)
            
            # Simulate model loading (in real implementation, would use actual framework)
            import time
            start_time = time.time()
            
            # Here you would actually load the model with PyTorch, TensorFlow, etc.
            # For now, we just simulate it
            time.sleep(0.1)  # Simulate loading time
            
            load_time = time.time() - start_time
            
            loaded_model = LoadedModel(
                metadata=metadata,
                status=ModelStatus.LOADED,
                path=model_path,
                memory_usage_gb=metadata.size_gb,
                gpu_id=gpu_id,
                load_time_seconds=load_time
            )
            
            self.loaded_models[model_id] = loaded_model
            
            # Update last accessed
            metadata.last_accessed = datetime.now()
            
            print(f"[MODEL] ✓ Loaded in {load_time:.2f}s")
            return True
            
        except Exception as e:
            print(f"[MODEL] ✗ Failed to load: {e}")
            return False
    
    def unload_model(self, model_id: str) -> bool:
        """Unload a model from memory"""
        if model_id not in self.loaded_models:
            print(f"[MODEL] Model not loaded: {model_id}")
            return False
        
        try:
            loaded_model = self.loaded_models[model_id]
            
            # Here you would actually unload the model and free memory
            # For now, we just remove from tracking
            
            del self.loaded_models[model_id]
            
            print(f"[MODEL] ✓ Unloaded: {loaded_model.metadata.name}")
            return True
            
        except Exception as e:
            print(f"[MODEL] ✗ Failed to unload: {e}")
            return False

    def _evict_loaded_if_needed(self, incoming_size_gb: float):
        """Evict least recently accessed loaded models to honor memory budget"""
        total = self.get_total_loaded_memory()
        budget = self.max_loaded_memory_gb
        if total + incoming_size_gb <= budget:
            return

        candidates = sorted(
            self.loaded_models.items(),
            key=lambda kv: kv[1].metadata.last_accessed
        )
        for model_id, loaded in candidates:
            if total + incoming_size_gb <= budget:
                break
            self.unload_model(model_id)
            total -= loaded.memory_usage_gb
    
    def list_models(self, framework: Optional[ModelFramework] = None,
                   model_type: Optional[ModelType] = None) -> List[ModelMetadata]:
        """List available models with optional filtering"""
        models = list(self.model_registry.values())
        
        if framework:
            models = [m for m in models if m.framework == framework]
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        return models
    
    def get_loaded_models(self) -> List[LoadedModel]:
        """Get all loaded models"""
        return list(self.loaded_models.values())
    
    def get_model_info(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata"""
        return self.model_registry.get(model_id)
    
    def estimate_memory_required(self, model_id: str) -> float:
        """Estimate memory required to load model"""
        if model_id not in self.model_registry:
            return 0.0
        
        metadata = self.model_registry[model_id]
        
        # Estimate: model size + overhead (2x for inference, 4x for training)
        return metadata.size_gb * 2.0
    
    def can_load_model(self, model_id: str, available_memory_gb: float) -> bool:
        """Check if model can be loaded given available memory"""
        required = self.estimate_memory_required(model_id)
        return required <= available_memory_gb
    
    def get_total_loaded_memory(self) -> float:
        """Get total memory used by loaded models"""
        return sum(m.memory_usage_gb for m in self.loaded_models.values())
    
    def print_summary(self):
        """Print model manager summary"""
        print("\n" + "="*80)
        print("MODEL MANAGER SUMMARY")
        print("="*80)
        
        print(f"\nTotal Models: {len(self.model_registry)}")
        print(f"Loaded Models: {len(self.loaded_models)}")
        print(f"Cache Size: {self.cache.get_cache_size_gb():.2f} GB")
        print(f"Memory Used: {self.get_total_loaded_memory():.2f} GB")
        
        if self.loaded_models:
            print("\nLoaded Models:")
            print("-" * 80)
            for model_id, loaded in self.loaded_models.items():
                print(f"  {loaded.metadata.name} ({loaded.metadata.framework.value})")
                print(f"    Memory: {loaded.memory_usage_gb:.2f} GB")
                if loaded.gpu_id is not None:
                    print(f"    GPU: {loaded.gpu_id}")
        
        print("\n" + "="*80 + "\n")


# Predefined model templates
class ModelTemplates:
    """Predefined model metadata templates"""
    
    @staticmethod
    def llama_7b() -> ModelMetadata:
        """LLaMA 7B model"""
        return ModelMetadata(
            model_id="llama-7b",
            name="LLaMA 7B",
            framework=ModelFramework.PYTORCH,
            model_type=ModelType.LLM,
            version="1.0",
            size_gb=13.5,
            parameters_millions=7000,
            description="LLaMA 7B language model",
            tags=["llm", "language", "generative"]
        )
    
    @staticmethod
    def stable_diffusion() -> ModelMetadata:
        """Stable Diffusion model"""
        return ModelMetadata(
            model_id="stable-diffusion-v1-5",
            name="Stable Diffusion v1.5",
            framework=ModelFramework.PYTORCH,
            model_type=ModelType.GENERATIVE,
            version="1.5",
            size_gb=4.0,
            parameters_millions=890,
            description="Text-to-image generation model",
            tags=["diffusion", "image", "generative"]
        )
    
    @staticmethod
    def resnet50() -> ModelMetadata:
        """ResNet-50 model"""
        return ModelMetadata(
            model_id="resnet50",
            name="ResNet-50",
            framework=ModelFramework.PYTORCH,
            model_type=ModelType.VISION,
            version="1.0",
            size_gb=0.1,
            parameters_millions=25,
            description="Image classification model",
            tags=["vision", "classification"]
        )


if __name__ == "__main__":
    # Test model manager
    manager = ModelManager()
    manager.print_summary()
