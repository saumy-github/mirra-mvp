#!/usr/bin/env python3
from typing import Dict, Any
import numpy as np

from pipeline_star.star_runner import generate_apose_mesh
from pipeline_star.mesh_measure import extract_measurements_from_mesh


FITTING_WEIGHTS = {
    'height_cm': 1.0,
    'shoulder_width_cm': 1.0,
    'chest_circumference_cm': 1.0,
    'waist_circumference_cm': 1.0,
    'hip_circumference_cm': 1.0,
}

BETA_REGULARIZATION_LAMBDA = 0.01

OPTIMIZER_MAX_ITERATIONS = 100
OPTIMIZER_LEARNING_RATE = 0.1
OPTIMIZER_EPSILON = 1e-5
OPTIMIZER_CONVERGENCE_THRESHOLD = 1e-6
OPTIMIZER_CONVERGENCE_PATIENCE = 5
OPTIMIZER_PRINT_FREQUENCY = 10


# Predict measurements from betas by generating mesh and extracting measurements
def predict_measurements_from_betas(
    gender: str,
    betas: np.ndarray,
    scale: float = 1.0,
    num_betas: int = 10,
    debug: bool = False
) -> Dict[str, float]:
    mesh_data = generate_apose_mesh(gender, betas, scale, num_betas)
    vertices = mesh_data['vertices']
    measurements = extract_measurements_from_mesh(vertices, debug=debug)
    return measurements


# Compute weighted least-squares loss with L2 regularization: Σ weight * ((pred-target)/target)^2 + λ * ||betas||^2
def compute_fitting_loss(
    betas: np.ndarray,
    target_measurements: Dict[str, float],
    gender: str,
    scale: float = 1.0,
    num_betas: int = 10,
    debug: bool = False
) -> float:
    pred_measurements = predict_measurements_from_betas(gender, betas, scale, num_betas, debug=debug)
    
    total_loss = 0.0
    measurement_losses = {}
    
    for field, weight in FITTING_WEIGHTS.items():
        if field in target_measurements and field in pred_measurements:
            target = target_measurements[field]
            pred = pred_measurements[field]
            
            relative_error = (pred - target) / target if target > 0 else 0.0
            squared_error = relative_error ** 2
            weighted_error = weight * squared_error
            
            measurement_losses[field] = weighted_error
            total_loss += weighted_error
    
    regularization = BETA_REGULARIZATION_LAMBDA * np.sum(betas ** 2)
    total_loss += regularization
    
    if debug:
        print(f"[DEBUG] Loss breakdown:")
        for field, loss in measurement_losses.items():
            print(f"  {field}: {loss:.6f}")
        print(f"  regularization: {regularization:.6f}")
        print(f"  total_loss: {total_loss:.6f}")
    
    return total_loss


# Fit STAR betas to target measurements using finite-difference gradient descent
def fit_betas_to_measurements(
    target_measurements: Dict[str, float],
    gender: str,
    num_betas: int = 10,
    use_scale: bool = True
) -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("FITTING BETAS TO TARGET MEASUREMENTS")
    print("=" * 60)
    
    betas = np.zeros(num_betas)
    
    if use_scale and 'height_cm' in target_measurements:
        default_measurements = predict_measurements_from_betas(
            gender, betas, scale=1.0, num_betas=num_betas
        )
        default_height = default_measurements.get('height_cm', 170.0)
        target_height = target_measurements['height_cm']
        scale = target_height / default_height if default_height > 0 else 1.0
        print(f"Initial scale from height matching: {scale:.4f}")
    else:
        scale = 1.0
        print("Using fixed scale: 1.0")
    
    current_loss = compute_fitting_loss(
        betas, target_measurements, gender, scale, num_betas, debug=False
    )
    print(f"\nInitial loss: {current_loss:.6f}")
    
    loss_history = [current_loss]
    no_improvement_count = 0
    
    for iteration in range(OPTIMIZER_MAX_ITERATIONS):
        gradient = np.zeros(num_betas)
        
        for i in range(num_betas):
            betas_plus = betas.copy()
            betas_plus[i] += OPTIMIZER_EPSILON
            
            loss_plus = compute_fitting_loss(
                betas_plus, target_measurements, gender, scale, num_betas, debug=False
            )
            
            gradient[i] = (loss_plus - current_loss) / OPTIMIZER_EPSILON
        
        betas = betas - OPTIMIZER_LEARNING_RATE * gradient
        
        new_loss = compute_fitting_loss(
            betas, target_measurements, gender, scale, num_betas, debug=False
        )
        
        loss_history.append(new_loss)
        loss_change = abs(current_loss - new_loss)
        current_loss = new_loss
        
        if (iteration + 1) % OPTIMIZER_PRINT_FREQUENCY == 0:
            pred_measurements = predict_measurements_from_betas(
                gender, betas, scale, num_betas, debug=False
            )
            print(f"\nIteration {iteration + 1}/{OPTIMIZER_MAX_ITERATIONS}")
            print(f"  Loss: {current_loss:.6f} (change: {loss_change:.6f})")
            print(f"  Predicted vs Target:")
            for field in ['height_cm', 'shoulder_width_cm', 'chest_circumference_cm', 
                          'waist_circumference_cm', 'hip_circumference_cm']:
                if field in target_measurements and field in pred_measurements:
                    pred = pred_measurements[field]
                    target = target_measurements[field]
                    error_pct = ((pred - target) / target * 100) if target > 0 else 0.0
                    print(f"    {field}: {pred:.2f} vs {target:.2f} (error: {error_pct:+.2f}%)")
        
        if loss_change < OPTIMIZER_CONVERGENCE_THRESHOLD:
            no_improvement_count += 1
            if no_improvement_count >= OPTIMIZER_CONVERGENCE_PATIENCE:
                print(
                    f"\nConverged after {iteration + 1} iterations "
                    f"(loss change < {OPTIMIZER_CONVERGENCE_THRESHOLD})"
                )
                break
        else:
            no_improvement_count = 0
    else:
        print(f"\nReached max iterations ({OPTIMIZER_MAX_ITERATIONS})")
    
    final_measurements = predict_measurements_from_betas(
        gender, betas, scale, num_betas, debug=False
    )
    
    print("\n" + "=" * 60)
    print("FITTING COMPLETE")
    print("=" * 60)
    print(f"Final loss: {current_loss:.6f}")
    print(f"Final scale: {scale:.4f}")
    print(f"Final betas: {betas}")
    print("=" * 60 + "\n")
    
    return {
        'betas': betas,
        'scale': scale,
        'loss': current_loss,
        'loss_history': loss_history,
        'predicted_measurements': final_measurements,
        'iterations': len(loss_history) - 1
    }
