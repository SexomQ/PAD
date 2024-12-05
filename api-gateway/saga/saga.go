package saga

import (
	"fmt"
	"runtime/debug"
	"sync"
)

// Action defines an action with its compensation function.
type Action struct {
	ActionFunc       func(args ...interface{}) (interface{}, error)
	CompensationFunc func(args ...interface{}) error
	Args             []interface{}
	Result           interface{}
}

// SagaError holds details about the saga failure and compensation issues.
type SagaError struct {
	FailedStepIndex            int
	ActionError                error
	ActionTraceback            string
	CompensationErrors         map[int]error
	CompensationErrorTraceback map[int]string
}

func (e SagaError) Error() string {
	msg := fmt.Sprintf("Transaction failed at step %d: %v\nTraceback:\n%s\n",
		e.FailedStepIndex, e.ActionError, e.ActionTraceback)

	if len(e.CompensationErrors) > 0 {
		msg += "Compensation errors:\n"
		for step, err := range e.CompensationErrors {
			traceback := e.CompensationErrorTraceback[step]
			msg += fmt.Sprintf("- Step %d: %v\nTraceback:\n%s\n", step, err, traceback)
		}
	}

	return msg
}

// Saga holds the steps to execute and manage.
type Saga struct {
	Steps []Action
	mu    sync.Mutex
}

type SagaPayload struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

// Execute runs the saga, executing actions and compensating on failure.
func (s *Saga) Execute(payload SagaPayload) error {
	var lastCompletedIndex int
	defer func() {
		if r := recover(); r != nil {
			fmt.Println("Recovered in saga execution:", r)
		}
	}()

	for i, step := range s.Steps {
		s.mu.Lock()
		result, err := step.ActionFunc(append(step.Args, payload)...)
		s.mu.Unlock()

		if err != nil {
			trace := string(debug.Stack())
			compensationErrors := s.runCompensations(i)
			return SagaError{
				FailedStepIndex:            i,
				ActionError:                err,
				ActionTraceback:            trace,
				CompensationErrors:         compensationErrors.Errors,
				CompensationErrorTraceback: compensationErrors.Tracebacks,
			}
		}

		// Save the result for possible use in compensation
		s.mu.Lock()
		s.Steps[i].Result = result
		s.mu.Unlock()

		lastCompletedIndex = i
	}

	fmt.Printf("Saga executed successfully. Completed steps: %d\n", lastCompletedIndex+1)
	return nil
}

// CompensationErrors holds errors during compensations.
type CompensationErrors struct {
	Errors     map[int]error
	Tracebacks map[int]string
}

// runCompensations performs compensations in reverse order.
func (s *Saga) runCompensations(lastActionIndex int) CompensationErrors {
	errors := make(map[int]error)
	tracebacks := make(map[int]string)

	for i := lastActionIndex - 1; i >= 0; i-- {
		step := s.Steps[i]
		err := step.CompensationFunc(step.Args...)
		if err != nil {
			errors[i] = err
			tracebacks[i] = string(debug.Stack())
		}
	}

	return CompensationErrors{Errors: errors, Tracebacks: tracebacks}
}

// OrchestrationBuilder helps build a saga.
type OrchestrationBuilder struct {
	Steps []Action
}

// AddStep adds a new action and its compensation to the saga.
func (b *OrchestrationBuilder) AddStep(action func(args ...interface{}) (interface{}, error), compensation func(args ...interface{}) error) *OrchestrationBuilder {
	b.Steps = append(b.Steps, Action{ActionFunc: action, CompensationFunc: compensation})
	return b
}

// Build builds the saga.
func (b *OrchestrationBuilder) Build() *Saga {
	return &Saga{Steps: b.Steps}
}
