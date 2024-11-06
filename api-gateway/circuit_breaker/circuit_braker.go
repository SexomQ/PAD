package circuit_breaker

import (
	"errors"
	"log"
	"sync"
	"time"
)

type CircuitBreaker struct {
	FailureCount    int
	FailureLimit    int
	State           string
	LastFailureTime time.Time
	Lock            sync.Mutex
	Timeout         time.Duration
}

const (
	ClosedState   = "CLOSED"
	OpenState     = "OPEN"
	HalfOpenState = "HALF_OPEN"
)

func NewCircuitBreaker(failureLimit int, timeout time.Duration) *CircuitBreaker {
	return &CircuitBreaker{
		FailureLimit: failureLimit,
		State:        ClosedState,
		Timeout:      timeout,
	}
}

func (cb *CircuitBreaker) Call(f func() error) error {
	cb.Lock.Lock()
	defer cb.Lock.Unlock()

	if cb.State == OpenState {
		// Check if the timeout duration has passed, allowing switch to Half-Open state
		if time.Since(cb.LastFailureTime) > cb.Timeout {
			cb.State = HalfOpenState
			log.Println("Circuit breaker transitioning to HALF_OPEN state")
		} else {
			log.Println("Circuit breaker OPEN, skipping call")
			return errors.New("circuit breaker is open")
		}
	}

	var err error
	cb.FailureCount = 0 // Reset failure count at the beginning of each Call attempt

	// Retry loop up to FailureLimit times
	for attempt := 0; attempt < cb.FailureLimit; attempt++ {
		err = f()
		if err == nil {
			// Success: Reset failure count and state
			if cb.State == HalfOpenState {
				cb.State = ClosedState
				log.Println("Circuit breaker resetting to CLOSED state after successful call")
			}
			cb.FailureCount = 0
			log.Println("Request succeeded, resetting failure count")
			return nil
		}

		// Log the failure and increment failure count
		cb.FailureCount++
		log.Printf("Request failed on attempt %d, error: %v. Failure count: %d", attempt+1, err, cb.FailureCount)
	}

	// All retries failed, so trip the breaker
	cb.LastFailureTime = time.Now()
	cb.State = OpenState
	log.Println("Circuit breaker tripped to OPEN state after reaching failure limit")
	return errors.New("request failed after maximum retry attempts")
}
