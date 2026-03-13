package collector

import (
	"testing"
)

// TestGetContainerLogs tests the log fetching functionality
func TestGetContainerLogs(t *testing.T) {
	// Note: These are unit tests that would require Docker to be running
	// In a real scenario, you'd use mocking or integration tests
	
	t.Run("GetContainerLogs with invalid container", func(t *testing.T) {
		logs, err := GetContainerLogs("nonexistent-container", 100, 0)
		
		// Should return error for nonexistent container
		if err == nil {
			t.Error("Expected error for nonexistent container, got nil")
		}
		
		if logs != nil {
			t.Errorf("Expected nil logs for nonexistent container, got %v", logs)
		}
	})
	
	t.Run("GetContainerLogs with zero tail", func(t *testing.T) {
		// Should handle edge case of 0 tail
		_, err := GetContainerLogs("test-container", 0, 0)
		// Error is expected for nonexistent container, but call shouldn't panic
		_ = err
	})
}

// TestInspectContainer tests container inspection
func TestInspectContainer(t *testing.T) {
	t.Run("InspectContainer with invalid container", func(t *testing.T) {
		inspect, err := InspectContainer("nonexistent-container")
		
		if err == nil {
			t.Error("Expected error for nonexistent container, got nil")
		}
		
		if inspect != nil {
			t.Errorf("Expected nil inspect data for nonexistent container, got %v", inspect)
		}
	})
}

// TestRemoveContainer tests container removal
func TestRemoveContainer(t *testing.T) {
	t.Run("RemoveContainer with invalid container", func(t *testing.T) {
		err := RemoveContainer("nonexistent-container", false, false)
		
		if err == nil {
			t.Error("Expected error for nonexistent container, got nil")
		}
	})
	
	t.Run("RemoveContainer with force and volumes flags", func(t *testing.T) {
		// Test that function accepts parameters correctly
		err := RemoveContainer("test-container", true, true)
		// Error expected for nonexistent container, but call shouldn't panic
		_ = err
	})
}

// TestExecCreate tests exec creation
func TestExecCreate(t *testing.T) {
	t.Run("ExecCreate with invalid container", func(t *testing.T) {
		execID, err := ExecCreate("nonexistent-container", []string{"/bin/bash"}, true)
		
		if err == nil {
			t.Error("Expected error for nonexistent container, got nil")
		}
		
		if execID != "" {
			t.Errorf("Expected empty exec ID for nonexistent container, got %s", execID)
		}
	})
	
	t.Run("ExecCreate with valid parameters", func(t *testing.T) {
		// Test that function accepts different command formats
		_, err := ExecCreate("test-container", []string{"/bin/sh", "-c", "echo test"}, false)
		// Error expected for nonexistent container, but call shouldn't panic
		_ = err
	})
	
	t.Run("ExecCreate with empty command", func(t *testing.T) {
		// Test edge case of empty command
		_, err := ExecCreate("test-container", []string{}, true)
		// Should handle gracefully
		_ = err
	})
}

// TestStartContainer tests starting containers
func TestStartContainer(t *testing.T) {
	t.Run("StartContainer with invalid container", func(t *testing.T) {
		err := StartContainer("nonexistent-container")
		
		if err == nil {
			t.Error("Expected error for nonexistent container, got nil")
		}
	})
}

// TestStopContainer tests stopping containers
func TestStopContainer(t *testing.T) {
	t.Run("StopContainer with invalid container", func(t *testing.T) {
		err := StopContainer("nonexistent-container")
		
		if err == nil {
			t.Error("Expected error for nonexistent container, got nil")
		}
	})
}

// TestRestartContainer tests restarting containers
func TestRestartContainer(t *testing.T) {
	t.Run("RestartContainer with invalid container", func(t *testing.T) {
		err := RestartContainer("nonexistent-container")
		
		if err == nil {
			t.Error("Expected error for nonexistent container, got nil")
		}
	})
}

// TestKillContainer tests killing containers
func TestKillContainer(t *testing.T) {
	t.Run("KillContainer with invalid container", func(t *testing.T) {
		err := KillContainer("nonexistent-container")
		
		if err == nil {
			t.Error("Expected error for nonexistent container, got nil")
		}
	})
}

// TestGetDockerContainers tests listing containers
func TestGetDockerContainers(t *testing.T) {
	t.Run("GetDockerContainers returns without panic", func(t *testing.T) {
		// Function should not panic even if Docker is not available
		containers := GetDockerContainers()
		// May be nil if Docker is not running, which is expected
		_ = containers
	})
}

// Benchmark tests for performance
func BenchmarkGetContainerLogs(b *testing.B) {
	for i := 0; i < b.N; i++ {
		_, _ = GetContainerLogs("test-container", 100, 0)
	}
}

func BenchmarkInspectContainer(b *testing.B) {
	for i := 0; i < b.N; i++ {
		_, _ = InspectContainer("test-container")
	}
}
