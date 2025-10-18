#!/usr/bin/env python3
"""
Lucid Session Management Pipeline State Machine
Handles state transitions for session processing pipelines
"""

from enum import Enum
from typing import Dict, Set, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

class PipelineState(Enum):
    """Pipeline states"""
    CREATED = "created"
    STARTING = "starting"
    ACTIVE = "active"
    PAUSING = "pausing"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    CLEANUP = "cleanup"
    DESTROYED = "destroyed"

class StateTransition(Enum):
    """State transition triggers"""
    START = "start"
    START_COMPLETE = "start_complete"
    PAUSE = "pause"
    PAUSE_COMPLETE = "pause_complete"
    RESUME = "resume"
    RESUME_COMPLETE = "resume_complete"
    STOP = "stop"
    STOP_COMPLETE = "stop_complete"
    ERROR = "error"
    RECOVER = "recover"
    CLEANUP = "cleanup"
    CLEANUP_COMPLETE = "cleanup_complete"
    DESTROY = "destroy"

@dataclass
class StateTransitionRule:
    """State transition rule"""
    from_state: PipelineState
    transition: StateTransition
    to_state: PipelineState
    description: str

class PipelineStateMachine:
    """
    State machine for session processing pipelines
    Manages valid state transitions and enforces pipeline lifecycle
    """
    
    def __init__(self):
        self.transition_rules = self._initialize_transition_rules()
        self.current_state: Optional[PipelineState] = None
        self.state_history: list = []
        
        logger.info("Pipeline State Machine initialized")
    
    def _initialize_transition_rules(self) -> Dict[PipelineState, Dict[StateTransition, StateTransitionRule]]:
        """Initialize state transition rules"""
        rules = {}
        
        # Define valid transitions for each state
        state_transitions = {
            PipelineState.CREATED: [
                StateTransitionRule(
                    PipelineState.CREATED, StateTransition.START, PipelineState.STARTING,
                    "Start pipeline initialization"
                ),
                StateTransitionRule(
                    PipelineState.CREATED, StateTransition.ERROR, PipelineState.ERROR,
                    "Pipeline creation error"
                ),
                StateTransitionRule(
                    PipelineState.CREATED, StateTransition.DESTROY, PipelineState.DESTROYED,
                    "Destroy pipeline without starting"
                )
            ],
            
            PipelineState.STARTING: [
                StateTransitionRule(
                    PipelineState.STARTING, StateTransition.START_COMPLETE, PipelineState.ACTIVE,
                    "Pipeline start completed successfully"
                ),
                StateTransitionRule(
                    PipelineState.STARTING, StateTransition.ERROR, PipelineState.ERROR,
                    "Pipeline start failed"
                ),
                StateTransitionRule(
                    PipelineState.STARTING, StateTransition.STOP, PipelineState.STOPPING,
                    "Stop pipeline during startup"
                )
            ],
            
            PipelineState.ACTIVE: [
                StateTransitionRule(
                    PipelineState.ACTIVE, StateTransition.PAUSE, PipelineState.PAUSING,
                    "Pause active pipeline"
                ),
                StateTransitionRule(
                    PipelineState.ACTIVE, StateTransition.STOP, PipelineState.STOPPING,
                    "Stop active pipeline"
                ),
                StateTransitionRule(
                    PipelineState.ACTIVE, StateTransition.ERROR, PipelineState.ERROR,
                    "Pipeline processing error"
                )
            ],
            
            PipelineState.PAUSING: [
                StateTransitionRule(
                    PipelineState.PAUSING, StateTransition.PAUSE_COMPLETE, PipelineState.PAUSED,
                    "Pipeline pause completed"
                ),
                StateTransitionRule(
                    PipelineState.PAUSING, StateTransition.ERROR, PipelineState.ERROR,
                    "Pipeline pause failed"
                ),
                StateTransitionRule(
                    PipelineState.PAUSING, StateTransition.STOP, PipelineState.STOPPING,
                    "Stop pipeline during pause"
                )
            ],
            
            PipelineState.PAUSED: [
                StateTransitionRule(
                    PipelineState.PAUSED, StateTransition.RESUME, PipelineState.ACTIVE,
                    "Resume paused pipeline"
                ),
                StateTransitionRule(
                    PipelineState.PAUSED, StateTransition.STOP, PipelineState.STOPPING,
                    "Stop paused pipeline"
                ),
                StateTransitionRule(
                    PipelineState.PAUSED, StateTransition.ERROR, PipelineState.ERROR,
                    "Pipeline error while paused"
                )
            ],
            
            PipelineState.STOPPING: [
                StateTransitionRule(
                    PipelineState.STOPPING, StateTransition.STOP_COMPLETE, PipelineState.STOPPED,
                    "Pipeline stop completed"
                ),
                StateTransitionRule(
                    PipelineState.STOPPING, StateTransition.ERROR, PipelineState.ERROR,
                    "Pipeline stop failed"
                )
            ],
            
            PipelineState.STOPPED: [
                StateTransitionRule(
                    PipelineState.STOPPED, StateTransition.CLEANUP, PipelineState.CLEANUP,
                    "Cleanup stopped pipeline"
                ),
                StateTransitionRule(
                    PipelineState.STOPPED, StateTransition.DESTROY, PipelineState.DESTROYED,
                    "Destroy stopped pipeline"
                ),
                StateTransitionRule(
                    PipelineState.STOPPED, StateTransition.RECOVER, PipelineState.CREATED,
                    "Recover pipeline for restart"
                )
            ],
            
            PipelineState.ERROR: [
                StateTransitionRule(
                    PipelineState.ERROR, StateTransition.RECOVER, PipelineState.CREATED,
                    "Recover from error state"
                ),
                StateTransitionRule(
                    PipelineState.ERROR, StateTransition.CLEANUP, PipelineState.CLEANUP,
                    "Cleanup after error"
                ),
                StateTransitionRule(
                    PipelineState.ERROR, StateTransition.DESTROY, PipelineState.DESTROYED,
                    "Destroy after error"
                )
            ],
            
            PipelineState.CLEANUP: [
                StateTransitionRule(
                    PipelineState.CLEANUP, StateTransition.CLEANUP_COMPLETE, PipelineState.DESTROYED,
                    "Cleanup completed"
                ),
                StateTransitionRule(
                    PipelineState.CLEANUP, StateTransition.ERROR, PipelineState.ERROR,
                    "Cleanup failed"
                )
            ],
            
            PipelineState.DESTROYED: [
                # No transitions from destroyed state
            ]
        }
        
        # Build transition rules dictionary
        for state, transitions in state_transitions.items():
            rules[state] = {}
            for rule in transitions:
                rules[state][rule.transition] = rule
        
        return rules
    
    def can_transition(self, from_state: PipelineState, to_state: PipelineState) -> bool:
        """
        Check if a transition from one state to another is valid
        
        Args:
            from_state: Current state
            to_state: Target state
            
        Returns:
            bool: True if transition is valid
        """
        if from_state not in self.transition_rules:
            logger.warning(f"No transition rules defined for state {from_state}")
            return False
        
        # Check if any transition leads to the target state
        for transition, rule in self.transition_rules[from_state].items():
            if rule.to_state == to_state:
                return True
        
        return False
    
    def can_transition_with_trigger(
        self, 
        from_state: PipelineState, 
        transition: StateTransition
    ) -> bool:
        """
        Check if a transition with a specific trigger is valid
        
        Args:
            from_state: Current state
            transition: Transition trigger
            
        Returns:
            bool: True if transition is valid
        """
        if from_state not in self.transition_rules:
            return False
        
        return transition in self.transition_rules[from_state]
    
    def get_valid_transitions(self, from_state: PipelineState) -> Set[StateTransition]:
        """
        Get all valid transitions from a state
        
        Args:
            from_state: Current state
            
        Returns:
            Set of valid transition triggers
        """
        if from_state not in self.transition_rules:
            return set()
        
        return set(self.transition_rules[from_state].keys())
    
    def get_next_states(self, from_state: PipelineState) -> Set[PipelineState]:
        """
        Get all possible next states from a state
        
        Args:
            from_state: Current state
            
        Returns:
            Set of possible next states
        """
        if from_state not in self.transition_rules:
            return set()
        
        next_states = set()
        for rule in self.transition_rules[from_state].values():
            next_states.add(rule.to_state)
        
        return next_states
    
    def transition(
        self, 
        from_state: PipelineState, 
        transition: StateTransition
    ) -> PipelineState:
        """
        Perform a state transition
        
        Args:
            from_state: Current state
            transition: Transition trigger
            
        Returns:
            PipelineState: New state after transition
            
        Raises:
            ValueError: If transition is not valid
        """
        if not self.can_transition_with_trigger(from_state, transition):
            valid_transitions = self.get_valid_transitions(from_state)
            raise ValueError(
                f"Invalid transition {transition} from state {from_state}. "
                f"Valid transitions: {valid_transitions}"
            )
        
        rule = self.transition_rules[from_state][transition]
        new_state = rule.to_state
        
        # Record transition in history
        self.state_history.append({
            "from_state": from_state.value,
            "transition": transition.value,
            "to_state": new_state.value,
            "description": rule.description
        })
        
        # Update current state
        self.current_state = new_state
        
        logger.info(
            f"State transition: {from_state.value} --[{transition.value}]--> {new_state.value} "
            f"({rule.description})"
        )
        
        return new_state
    
    def get_state_history(self) -> list:
        """Get the state transition history"""
        return self.state_history.copy()
    
    def get_current_state(self) -> Optional[PipelineState]:
        """Get the current state"""
        return self.current_state
    
    def is_terminal_state(self, state: PipelineState) -> bool:
        """
        Check if a state is terminal (no further transitions possible)
        
        Args:
            state: State to check
            
        Returns:
            bool: True if state is terminal
        """
        return state == PipelineState.DESTROYED
    
    def is_error_state(self, state: PipelineState) -> bool:
        """
        Check if a state represents an error condition
        
        Args:
            state: State to check
            
        Returns:
            bool: True if state is an error state
        """
        return state == PipelineState.ERROR
    
    def is_active_state(self, state: PipelineState) -> bool:
        """
        Check if a state represents an active pipeline
        
        Args:
            state: State to check
            
        Returns:
            bool: True if state represents active processing
        """
        return state in [PipelineState.ACTIVE, PipelineState.STARTING, PipelineState.PAUSING]
    
    def reset(self):
        """Reset the state machine"""
        self.current_state = None
        self.state_history.clear()
        logger.info("State machine reset")
    
    def get_state_info(self, state: PipelineState) -> Dict[str, any]:
        """
        Get detailed information about a state
        
        Args:
            state: State to get info for
            
        Returns:
            Dictionary with state information
        """
        return {
            "state": state.value,
            "is_terminal": self.is_terminal_state(state),
            "is_error": self.is_error_state(state),
            "is_active": self.is_active_state(state),
            "valid_transitions": [t.value for t in self.get_valid_transitions(state)],
            "possible_next_states": [s.value for s in self.get_next_states(state)]
        }
    
    def validate_pipeline_lifecycle(self, states: list) -> bool:
        """
        Validate a complete pipeline lifecycle
        
        Args:
            states: List of states in lifecycle order
            
        Returns:
            bool: True if lifecycle is valid
        """
        if not states:
            return False
        
        # Must start with CREATED
        if states[0] != PipelineState.CREATED:
            logger.error("Pipeline lifecycle must start with CREATED state")
            return False
        
        # Must end with DESTROYED
        if states[-1] != PipelineState.DESTROYED:
            logger.error("Pipeline lifecycle must end with DESTROYED state")
            return False
        
        # Validate transitions between consecutive states
        for i in range(len(states) - 1):
            current_state = states[i]
            next_state = states[i + 1]
            
            if not self.can_transition(current_state, next_state):
                logger.error(
                    f"Invalid transition from {current_state.value} to {next_state.value}"
                )
                return False
        
        return True
    
    def get_shortest_path(self, from_state: PipelineState, to_state: PipelineState) -> Optional[list]:
        """
        Get the shortest path between two states
        
        Args:
            from_state: Starting state
            to_state: Target state
            
        Returns:
            List of transitions or None if no path exists
        """
        if from_state == to_state:
            return []
        
        # Use BFS to find shortest path
        from collections import deque
        
        queue = deque([(from_state, [])])
        visited = {from_state}
        
        while queue:
            current_state, path = queue.popleft()
            
            if current_state == to_state:
                return path
            
            for transition in self.get_valid_transitions(current_state):
                rule = self.transition_rules[current_state][transition]
                next_state = rule.to_state
                
                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [transition]))
        
        return None
