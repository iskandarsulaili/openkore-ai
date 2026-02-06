"""
Reinforcement Learning Optimizer for Macro Parameters

Uses PPO (Proximal Policy Optimization) to fine-tune macro parameters
based on gameplay outcomes.
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional
from loguru import logger


class MacroReinforcementLearner:
    """
    Reinforcement learning agent for macro parameter optimization.
    Uses PPO (Proximal Policy Optimization) to fine-tune macro parameters.
    """
    
    def __init__(
        self,
        state_dim: int = 50,
        action_dim: int = 20,
        hidden_dim: int = 128,
        learning_rate_actor: float = 0.0003,
        learning_rate_critic: float = 0.001,
        gamma: float = 0.99,
        clip_epsilon: float = 0.2
    ):
        """
        Initialize RL optimizer.
        
        Args:
            state_dim: Dimension of game state features
            action_dim: Number of possible parameter adjustments
            hidden_dim: Hidden layer size
            learning_rate_actor: Learning rate for policy network
            learning_rate_critic: Learning rate for value network
            gamma: Discount factor for future rewards
            clip_epsilon: PPO clipping parameter
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.clip_epsilon = clip_epsilon
        
        # Actor network (policy)
        self.actor = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )
        
        # Critic network (value function)
        self.critic = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        
        # Optimizers
        self.optimizer_actor = torch.optim.Adam(
            self.actor.parameters(),
            lr=learning_rate_actor
        )
        self.optimizer_critic = torch.optim.Adam(
            self.critic.parameters(),
            lr=learning_rate_critic
        )
        
        # Training history
        self.training_history = []
        
        logger.info(
            f"Initialized RL optimizer with state_dim={state_dim}, "
            f"action_dim={action_dim}"
        )
    
    def select_action(
        self,
        state: np.ndarray,
        deterministic: bool = False
    ) -> Tuple[int, float]:
        """
        Select macro parameter adjustment based on current state.
        
        Args:
            state: Current game state features
            deterministic: If True, select best action (no exploration)
            
        Returns:
            (action, log_prob) tuple
        """
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        
        with torch.no_grad():
            action_probs = self.actor(state_tensor)
        
        if deterministic:
            # Greedy action selection
            action = torch.argmax(action_probs, dim=-1).item()
        else:
            # Sample from distribution
            action = torch.multinomial(action_probs, 1).item()
        
        # Calculate log probability for training
        log_prob = torch.log(action_probs[0, action]).item()
        
        return action, log_prob
    
    def update(
        self,
        states: torch.Tensor,
        actions: torch.Tensor,
        old_log_probs: torch.Tensor,
        rewards: torch.Tensor,
        next_states: torch.Tensor,
        dones: torch.Tensor
    ) -> Dict[str, float]:
        """
        PPO update step.
        
        Args:
            states: Batch of states
            actions: Batch of actions taken
            old_log_probs: Log probabilities of actions (from old policy)
            rewards: Batch of rewards received
            next_states: Batch of next states
            dones: Batch of done flags
            
        Returns:
            Dictionary with loss metrics
        """
        # Compute TD errors (advantages)
        with torch.no_grad():
            values = self.critic(states).squeeze()
            next_values = self.critic(next_states).squeeze()
            td_targets = rewards + self.gamma * next_values * (1 - dones)
            advantages = td_targets - values
            # Normalize advantages
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # Compute current action probabilities
        action_probs = self.actor(states)
        current_log_probs = torch.log(
            action_probs.gather(1, actions.unsqueeze(1)).squeeze()
        )
        
        # PPO policy loss with clipping
        ratio = torch.exp(current_log_probs - old_log_probs)
        clipped_ratio = torch.clamp(
            ratio,
            1 - self.clip_epsilon,
            1 + self.clip_epsilon
        )
        actor_loss = -torch.min(
            ratio * advantages,
            clipped_ratio * advantages
        ).mean()
        
        # Value function loss
        values = self.critic(states).squeeze()
        critic_loss = nn.MSELoss()(values, td_targets)
        
        # Update actor
        self.optimizer_actor.zero_grad()
        actor_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.actor.parameters(), 0.5)
        self.optimizer_actor.step()
        
        # Update critic
        self.optimizer_critic.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic.parameters(), 0.5)
        self.optimizer_critic.step()
        
        # Log metrics
        metrics = {
            "actor_loss": actor_loss.item(),
            "critic_loss": critic_loss.item(),
            "mean_advantage": advantages.mean().item(),
            "mean_value": values.mean().item()
        }
        
        self.training_history.append(metrics)
        
        return metrics
    
    def optimize_macro_parameters(
        self,
        macro: Dict,
        game_state: Dict,
        num_iterations: int = 10
    ) -> Dict:
        """
        Optimize macro parameters using RL.
        
        Args:
            macro: Macro configuration to optimize
            game_state: Current game state
            num_iterations: Number of optimization iterations
            
        Returns:
            Optimized macro configuration
        """
        state_features = self._extract_state_features(game_state)
        
        best_macro = macro.copy()
        best_reward = float('-inf')
        
        for _ in range(num_iterations):
            # Select parameter adjustment
            action, _ = self.select_action(state_features)
            
            # Apply adjustment to macro
            adjusted_macro = self._apply_adjustment(macro, action)
            
            # Simulate reward (would be actual gameplay outcome in production)
            reward = self._simulate_reward(adjusted_macro, game_state)
            
            if reward > best_reward:
                best_reward = reward
                best_macro = adjusted_macro
        
        logger.info(
            f"Optimized macro parameters: "
            f"reward improved from 0 to {best_reward:.2f}"
        )
        
        return best_macro
    
    def _extract_state_features(self, game_state: Dict) -> np.ndarray:
        """Extract numerical features from game state."""
        features = []
        
        # Health metrics
        features.append(game_state.get('hp_percent', 100) / 100.0)
        features.append(game_state.get('sp_percent', 100) / 100.0)
        
        # Combat metrics
        features.append(min(game_state.get('monsters_nearby', 0) / 10.0, 1.0))
        features.append(1.0 if game_state.get('in_combat', False) else 0.0)
        
        # Resource metrics
        features.append(game_state.get('weight_percent', 0) / 100.0)
        features.append(min(game_state.get('zeny', 0) / 1000000.0, 1.0))
        
        # Pad to state_dim
        while len(features) < self.state_dim:
            features.append(0.0)
        
        return np.array(features[:self.state_dim], dtype=np.float32)
    
    def _apply_adjustment(self, macro: Dict, action: int) -> Dict:
        """Apply parameter adjustment based on action."""
        adjusted = macro.copy()
        
        # Map action to parameter adjustment
        # Action 0-4: HP threshold adjustments
        # Action 5-9: Timeout adjustments
        # Action 10-14: Priority adjustments
        # Action 15-19: Other parameter adjustments
        
        if 'conditions' in adjusted:
            if action < 5 and 'hp' in adjusted['conditions']:
                # Adjust HP threshold
                delta = (action - 2) * 5  # -10, -5, 0, +5, +10
                adjusted['conditions']['hp'] = max(
                    10,
                    min(90, adjusted['conditions']['hp'] + delta)
                )
            elif action < 10 and 'timeout' in adjusted:
                # Adjust timeout
                delta = (action - 7) * 0.5
                adjusted['timeout'] = max(0.5, adjusted['timeout'] + delta)
        
        return adjusted
    
    def _simulate_reward(self, macro: Dict, game_state: Dict) -> float:
        """
        Simulate reward for macro (placeholder).
        In production, this would be actual gameplay outcome.
        """
        # Simple heuristic reward based on safety and efficiency
        reward = 0.0
        
        if 'conditions' in macro:
            conditions = macro['conditions']
            
            # Reward safe HP thresholds
            if 'hp' in conditions:
                hp_threshold = conditions['hp']
                if 20 <= hp_threshold <= 40:
                    reward += 1.0
                elif hp_threshold < 15 or hp_threshold > 50:
                    reward -= 0.5
            
            # Reward reasonable timeouts
            if 'timeout' in macro:
                timeout = macro['timeout']
                if 1.0 <= timeout <= 3.0:
                    reward += 0.5
        
        return reward
    
    def save_model(self, path: str):
        """Save model to disk."""
        torch.save({
            'actor_state_dict': self.actor.state_dict(),
            'critic_state_dict': self.critic.state_dict(),
            'optimizer_actor_state_dict': self.optimizer_actor.state_dict(),
            'optimizer_critic_state_dict': self.optimizer_critic.state_dict(),
            'training_history': self.training_history
        }, path)
        logger.info(f"Saved RL model to {path}")
    
    def load_model(self, path: str):
        """Load model from disk."""
        checkpoint = torch.load(path)
        self.actor.load_state_dict(checkpoint['actor_state_dict'])
        self.critic.load_state_dict(checkpoint['critic_state_dict'])
        self.optimizer_actor.load_state_dict(
            checkpoint['optimizer_actor_state_dict']
        )
        self.optimizer_critic.load_state_dict(
            checkpoint['optimizer_critic_state_dict']
        )
        self.training_history = checkpoint.get('training_history', [])
        logger.info(f"Loaded RL model from {path}")
    
    def get_training_statistics(self) -> Dict:
        """Get training statistics."""
        if not self.training_history:
            return {
                'total_updates': 0,
                'mean_actor_loss': 0.0,
                'mean_critic_loss': 0.0
            }
        
        return {
            'total_updates': len(self.training_history),
            'mean_actor_loss': np.mean([
                h['actor_loss'] for h in self.training_history[-100:]
            ]),
            'mean_critic_loss': np.mean([
                h['critic_loss'] for h in self.training_history[-100:]
            ]),
            'mean_advantage': np.mean([
                h['mean_advantage'] for h in self.training_history[-100:]
            ])
        }
