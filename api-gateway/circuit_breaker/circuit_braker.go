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
		// Check if timeout duration has passed, to switch to Half-Open state
		if time.Since(cb.LastFailureTime) > cb.Timeout {
			cb.State = HalfOpenState
			log.Println("Circuit breaker transitioning to HALF_OPEN state")
		} else {
			log.Println("Circuit breaker OPEN, skipping call")
			return errors.New("circuit breaker is open")
		}
	}

	err := f()

	if err != nil {
		cb.FailureCount++
		cb.LastFailureTime = time.Now()
		log.Printf("Request failed, error: %v. Failure count: %d", err, cb.FailureCount)

		if cb.FailureCount >= cb.FailureLimit {
			cb.State = OpenState
			log.Println("Circuit breaker tripped to OPEN state")
		}
		return err
	}

	// If the request succeeds, reset the failure count and state
	if cb.State == HalfOpenState {
		cb.State = ClosedState
		log.Println("Circuit breaker resetting to CLOSED state after successful call")
	}

	cb.FailureCount = 0
	log.Println("Request succeeded, resetting failure count")
	return nil
}
