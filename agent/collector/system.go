package collector

import (
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/load"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/shirou/gopsutil/v3/net"
)

type SystemMetrics struct {
	CPUUsage           float64
	LoadAverage        string
	MemoryUsed         float64
	MemoryFree         float64
	SwapUsed           float64
	DiskTotal          float64
	DiskUsed           float64
	DiskUsagePercent   float64
	TemperatureCPU     float64
	NetRx              float64
	NetTx              float64
}

type HostInfo struct {
	Hostname      string
	OS            string
	KernelVersion string
	CPUCores      int
	TotalMemory   float64
}

// GetSystemMetrics measures actual hardware state
func GetSystemMetrics() SystemMetrics {
	var metrics SystemMetrics

	// CPU
	cpuPercents, err := cpu.Percent(0, false)
	if err == nil && len(cpuPercents) > 0 {
		metrics.CPUUsage = cpuPercents[0]
	}

	loadStat, err := load.Avg()
	if err == nil {
		metrics.LoadAverage = fmt.Sprintf("%.2f, %.2f, %.2f", loadStat.Load1, loadStat.Load5, loadStat.Load15)
	}

	// Mem
	vMem, err := mem.VirtualMemory()
	if err == nil {
		metrics.MemoryUsed = float64(vMem.Used) / 1024 / 1024
		metrics.MemoryFree = float64(vMem.Free) / 1024 / 1024
	}

	sMem, err := mem.SwapMemory()
	if err == nil {
		metrics.SwapUsed = float64(sMem.Used) / 1024 / 1024
	}

	// Disk
	dStat, err := disk.Usage("/")
	if err == nil {
		metrics.DiskTotal = float64(dStat.Total) / 1024 / 1024 / 1024 // in GB
		metrics.DiskUsed = float64(dStat.Used) / 1024 / 1024 / 1024
		metrics.DiskUsagePercent = dStat.UsedPercent
	}

	// Temperatures
	metrics.TemperatureCPU = getCPUTemperature()

	// Net
	netStats, err := net.IOCounters(false)
	if err == nil && len(netStats) > 0 {
		metrics.NetRx = float64(netStats[0].BytesRecv)
		metrics.NetTx = float64(netStats[0].BytesSent)
	}

	return metrics
}

// getCPUTemperature tries multiple methods to read CPU temperature
func getCPUTemperature() float64 {
	// Method 1: Try gopsutil first
	temps, err := host.SensorsTemperatures()
	if err == nil {
		for _, temp := range temps {
			if temp.Temperature > 0 {
				return temp.Temperature
			}
		}
	}

	// Method 2: Read from /sys/class/thermal (coretemp)
	thermalZones := []string{
		"/sys/class/thermal/thermal_zone0/temp",
		"/sys/class/thermal/thermal_zone1/temp",
		"/sys/class/thermal/thermal_zone2/temp",
	}
	
	for _, zone := range thermalZones {
		data, err := os.ReadFile(zone)
		if err == nil {
			tempStr := strings.TrimSpace(string(data))
			if tempMilli, err := strconv.ParseFloat(tempStr, 64); err == nil {
				temp := tempMilli / 1000.0 // Convert from millidegrees
				if temp > 0 && temp < 150 { // Sanity check
					return temp
				}
			}
		}
	}

	// Method 3: Try sensors command
	cmd := exec.Command("sensors", "-u")
	output, err := cmd.Output()
	if err == nil {
		lines := strings.Split(string(output), "\n")
		for _, line := range lines {
			if strings.Contains(line, "temp1_input") || strings.Contains(line, "Package id 0") {
				fields := strings.Fields(line)
				if len(fields) >= 2 {
					if temp, err := strconv.ParseFloat(fields[len(fields)-1], 64); err == nil {
						if temp > 0 && temp < 150 {
							return temp
						}
					}
				}
			}
		}
	}

	return 0.0
}

func GetHostInfo() HostInfo {
	var info HostInfo
    
	hInfo, err := host.Info()
	if err == nil {
		info.Hostname = hInfo.Hostname
		info.OS = hInfo.OS
		info.KernelVersion = hInfo.KernelVersion
	}
    
	vMem, err := mem.VirtualMemory()
	if err == nil {
		info.TotalMemory = float64(vMem.Total) / 1024 / 1024 // in MB
	}
    
	cpuCores, err := cpu.Counts(true)
	if err == nil {
		info.CPUCores = cpuCores
	}
    
	return info
}
