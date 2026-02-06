"""
Model Optimization for Production Deployment

Provides GPU acceleration, model quantization, and ONNX export
for optimized ML inference.
"""

import torch
import torch.nn as nn
from torch.quantization import quantize_dynamic
from typing import Optional, Tuple
from loguru import logger
import time


class ModelOptimizer:
    """Optimize ML models for production deployment."""
    
    @staticmethod
    def quantize_model(model: nn.Module) -> nn.Module:
        """
        Apply dynamic quantization (int8) for faster inference.
        
        Reduces model size by ~4x and speeds up CPU inference by 2-4x
        with minimal accuracy loss (<1%).
        
        Args:
            model: PyTorch model to quantize
            
        Returns:
            Quantized model
        """
        logger.info("Quantizing model to int8...")
        
        # Apply dynamic quantization to Linear layers
        quantized = quantize_dynamic(
            model,
            {nn.Linear},
            dtype=torch.qint8
        )
        
        logger.info("Model quantization complete")
        return quantized
    
    @staticmethod
    def to_gpu_if_available(model: nn.Module) -> Tuple[nn.Module, str]:
        """
        Move model to GPU if CUDA available.
        
        Args:
            model: PyTorch model
            
        Returns:
            (model, device) tuple where device is 'cuda' or 'cpu'
        """
        if torch.cuda.is_available():
            device = 'cuda'
            model = model.cuda()
            logger.info(
                f"Model moved to GPU: {torch.cuda.get_device_name(0)}"
            )
        else:
            device = 'cpu'
            logger.info("GPU not available, using CPU")
        
        return model, device
    
    @staticmethod
    def export_onnx(
        model: nn.Module,
        input_shape: Tuple[int, ...],
        filename: str,
        opset_version: int = 14
    ):
        """
        Export model to ONNX format for optimized inference.
        
        ONNX models can be used with ONNX Runtime for faster inference
        across different platforms.
        
        Args:
            model: PyTorch model to export
            input_shape: Shape of input tensor (e.g., (1, 50))
            filename: Output filename (should end with .onnx)
            opset_version: ONNX opset version
        """
        logger.info(f"Exporting model to ONNX: {filename}")
        
        # Create dummy input
        dummy_input = torch.randn(input_shape)
        
        # Export
        torch.onnx.export(
            model,
            dummy_input,
            filename,
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={
                'input': {0: 'batch_size'},
                'output': {0: 'batch_size'}
            }
        )
        
        logger.info(f"ONNX export complete: {filename}")
    
    @staticmethod
    def benchmark_model(
        model: nn.Module,
        input_shape: Tuple[int, ...],
        num_iterations: int = 100,
        warmup: int = 10
    ) -> dict:
        """
        Benchmark model inference performance.
        
        Args:
            model: Model to benchmark
            input_shape: Input tensor shape
            num_iterations: Number of inference iterations
            warmup: Number of warmup iterations
            
        Returns:
            Dictionary with performance metrics
        """
        logger.info(f"Benchmarking model with {num_iterations} iterations...")
        
        # Create random input
        dummy_input = torch.randn(input_shape)
        
        # Move to same device as model
        try:
            device = next(model.parameters()).device
        except StopIteration:
            # Quantized models may not have parameters attribute
            device = torch.device('cpu')
        dummy_input = dummy_input.to(device)
        
        # Warmup
        model.eval()
        with torch.no_grad():
            for _ in range(warmup):
                _ = model(dummy_input)
        
        # Benchmark
        start_time = time.time()
        with torch.no_grad():
            for _ in range(num_iterations):
                _ = model(dummy_input)
        
        # Synchronize GPU if using CUDA
        if device.type == 'cuda':
            torch.cuda.synchronize()
        
        elapsed = time.time() - start_time
        
        # Prevent division by zero
        if elapsed == 0:
            elapsed = 0.0001
        
        metrics = {
            'total_time': elapsed,
            'avg_latency_ms': (elapsed / num_iterations) * 1000,
            'throughput': num_iterations / elapsed,
            'device': str(device)
        }
        
        logger.info(
            f"Benchmark complete: {metrics['avg_latency_ms']:.2f}ms "
            f"avg latency, {metrics['throughput']:.1f} inferences/sec"
        )
        
        return metrics
    
    @staticmethod
    def compare_optimizations(
        original_model: nn.Module,
        input_shape: Tuple[int, ...],
        num_iterations: int = 100
    ) -> dict:
        """
        Compare performance of different optimization techniques.
        
        Args:
            original_model: Original unoptimized model
            input_shape: Input tensor shape
            num_iterations: Number of benchmark iterations
            
        Returns:
            Dictionary with comparison results
        """
        results = {}
        
        # Benchmark original model (CPU)
        logger.info("Benchmarking original model (CPU)...")
        original_cpu = original_model.cpu()
        results['original_cpu'] = ModelOptimizer.benchmark_model(
            original_cpu, input_shape, num_iterations
        )
        
        # Benchmark quantized model
        logger.info("Benchmarking quantized model (CPU)...")
        quantized = ModelOptimizer.quantize_model(original_model)
        results['quantized_cpu'] = ModelOptimizer.benchmark_model(
            quantized, input_shape, num_iterations
        )
        
        # Benchmark GPU if available
        if torch.cuda.is_available():
            logger.info("Benchmarking GPU model...")
            gpu_model = original_model.cuda()
            results['gpu'] = ModelOptimizer.benchmark_model(
                gpu_model, input_shape, num_iterations
            )
        
        # Calculate speedups
        baseline = results['original_cpu']['avg_latency_ms']
        
        logger.info("\n=== Optimization Comparison ===")
        logger.info(
            f"Original (CPU): {results['original_cpu']['avg_latency_ms']:.2f}ms"
        )
        logger.info(
            f"Quantized (CPU): {results['quantized_cpu']['avg_latency_ms']:.2f}ms "
            f"({baseline / results['quantized_cpu']['avg_latency_ms']:.2f}x speedup)"
        )
        
        if 'gpu' in results:
            logger.info(
                f"GPU: {results['gpu']['avg_latency_ms']:.2f}ms "
                f"({baseline / results['gpu']['avg_latency_ms']:.2f}x speedup)"
            )
        
        return results


class CachedPredictor:
    """
    Caching layer for frequent macro pattern predictions.
    
    Reduces redundant predictions for similar game states.
    """
    
    def __init__(self, cache_size: int = 1000, similarity_threshold: float = 0.95):
        """
        Initialize cached predictor.
        
        Args:
            cache_size: Maximum number of cached predictions
            similarity_threshold: State similarity threshold for cache hit
        """
        self.cache = {}
        self.cache_size = cache_size
        self.similarity_threshold = similarity_threshold
        self.hits = 0
        self.misses = 0
        
        logger.info(
            f"Initialized prediction cache (size={cache_size}, "
            f"threshold={similarity_threshold})"
        )
    
    def get(self, state_features: torch.Tensor) -> Optional[torch.Tensor]:
        """
        Get cached prediction if available.
        
        Args:
            state_features: Input state features
            
        Returns:
            Cached prediction or None
        """
        # Convert to hashable key
        state_key = self._hash_state(state_features)
        
        if state_key in self.cache:
            self.hits += 1
            return self.cache[state_key]
        
        self.misses += 1
        return None
    
    def put(self, state_features: torch.Tensor, prediction: torch.Tensor):
        """
        Store prediction in cache.
        
        Args:
            state_features: Input state features
            prediction: Model prediction to cache
        """
        # Evict oldest entry if cache full
        if len(self.cache) >= self.cache_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        state_key = self._hash_state(state_features)
        self.cache[state_key] = prediction
    
    def _hash_state(self, state_features: torch.Tensor) -> str:
        """Create hash key from state features."""
        # Round to reduce sensitivity
        rounded = torch.round(state_features * 10) / 10
        return str(rounded.cpu().numpy().tobytes())
    
    def get_statistics(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'cache_size': len(self.cache)
        }
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Prediction cache cleared")
