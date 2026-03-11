'use client';

import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { Metric } from '@/lib/api';

interface MetricChartProps {
  data: Metric[];
  metricKey: keyof Metric;
  title: string;
  color: string;
  unit: string;
  height?: string;
}

export function MetricChart({ 
  data, 
  metricKey, 
  title, 
  color, 
  unit,
  height = '300px' 
}: MetricChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Inicializar o obtener instancia existente
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const chart = chartInstance.current;

    // Preparar datos para el gráfico
    const timestamps = data.map(m => new Date(m.timestamp).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }));
    
    const values = data.map(m => {
      const value = m[metricKey];
      return typeof value === 'number' ? Number(value.toFixed(2)) : 0;
    });

    // Configuración del gráfico
    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      title: {
        text: title,
        left: 'center',
        textStyle: {
          color: '#e0e0e0',
          fontSize: 14,
          fontWeight: 'normal'
        }
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(20, 20, 30, 0.9)',
        borderColor: color,
        borderWidth: 1,
        textStyle: {
          color: '#fff'
        },
        formatter: (params: any) => {
          if (Array.isArray(params) && params.length > 0) {
            const param = params[0];
            return `${param.axisValue}<br/>${param.marker}${param.seriesName}: ${param.value}${unit}`;
          }
          return '';
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: timestamps,
        boundaryGap: false,
        axisLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.2)'
          }
        },
        axisLabel: {
          color: '#999',
          fontSize: 10,
          interval: Math.floor(timestamps.length / 6) // Mostrar ~6 etiquetas
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.05)'
          }
        }
      },
      yAxis: {
        type: 'value',
        axisLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.2)'
          }
        },
        axisLabel: {
          color: '#999',
          fontSize: 10,
          formatter: (value: number) => `${value}${unit}`
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.05)'
          }
        }
      },
      series: [
        {
          name: title,
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          sampling: 'lttb',
          itemStyle: {
            color: color
          },
          lineStyle: {
            width: 2,
            color: color
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              {
                offset: 0,
                color: `${color}80` // 50% opacity
              },
              {
                offset: 1,
                color: `${color}10` // 6% opacity
              }
            ])
          },
          data: values
        }
      ]
    };

    chart.setOption(option);

    // Responsiveness
    const handleResize = () => {
      chart.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [data, metricKey, title, color, unit]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
    };
  }, []);

  return (
    <div 
      ref={chartRef} 
      style={{ 
        width: '100%', 
        height,
        minHeight: '200px'
      }} 
    />
  );
}
