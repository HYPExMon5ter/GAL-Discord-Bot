/**
 * Memory Leak Detection Script
 * Run this in the browser console to detect memory leaks
 */

(function() {
  console.log('🔍 Starting Memory Leak Detection...');
  
  let initialMemory = 0;
  let measurements = [];
  
  // Get current memory usage
  function getMemoryUsage() {
    if (performance.memory) {
      return {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      };
    }
    return null;
  }
  
  // Format bytes to MB
  function formatBytes(bytes) {
    return (bytes / 1024 / 1024).toFixed(2) + ' MB';
  }
  
  // Count intervals
  function countIntervals() {
    let count = 0;
    const originalSetInterval = window.setInterval;
    window.setInterval = function(...args) {
      count++;
      return originalSetInterval.apply(this, args);
    };
    return count;
  }
  
  // Count event listeners (approximation)
  function getEventListenerCount() {
    // This is a rough estimate - exact counting is difficult in JS
    const elements = document.querySelectorAll('*');
    let listenerCount = 0;
    elements.forEach(el => {
      if (el.addEventListener) {
        listenerCount += 1; // Estimate
      }
    });
    return listenerCount;
  }
  
  // Get component count
  function getComponentCount() {
    const reactComponents = document.querySelectorAll('[data-reactroot]');
    return reactComponents.length;
  }
  
  // Take measurement
  function takeMeasurement() {
    const memory = getMemoryUsage();
    if (!memory) {
      console.warn('Memory API not available');
      return;
    }
    
    const measurement = {
      timestamp: Date.now(),
      memory: memory.used,
      memoryMB: parseFloat(formatBytes(memory.used)),
      intervals: countIntervals(),
      listeners: getEventListenerCount(),
      components: getComponentCount()
    };
    
    measurements.push(measurement);
    return measurement;
  }
  
  // Analyze measurements
  function analyzeMeasurements() {
    if (measurements.length < 3) {
      console.log('Need at least 3 measurements to analyze');
      return;
    }
    
    const first = measurements[0];
    const last = measurements[measurements.length - 1];
    const timeDiff = (last.timestamp - first.timestamp) / 1000; // seconds
    const memoryDiff = last.memory - first.memory;
    const memoryRate = memoryDiff / timeDiff / 1024 / 1024; // MB/second
    
    console.log('\n📊 Memory Leak Analysis Results:');
    console.log('=====================================');
    console.log(`Time elapsed: ${timeDiff.toFixed(1)} seconds`);
    console.log(`Initial memory: ${formatBytes(first.memory)}`);
    console.log(`Final memory: ${formatBytes(last.memory)}`);
    console.log(`Memory change: ${memoryDiff > 0 ? '+' : ''}${formatBytes(memoryDiff)}`);
    console.log(`Memory rate: ${memoryRate > 0 ? '+' : ''}${memoryRate.toFixed(4)} MB/s`);
    
    // Check for leaks
    const leakThreshold = 1024 * 1024 * 10; // 10MB increase
    if (memoryDiff > leakThreshold) {
      console.error('🚨 MEMORY LEAK DETECTED!');
      console.error(`Memory increased by ${formatBytes(memoryDiff)} over ${timeDiff.toFixed(1)} seconds`);
    } else {
      console.log('✅ No significant memory leaks detected');
    }
    
    // Check interval growth
    const intervalGrowth = last.intervals - first.intervals;
    if (intervalGrowth > 5) {
      console.warn(`⚠️ Potential interval leak: ${intervalGrowth} new intervals created`);
    }
    
    return {
      memoryLeak: memoryDiff > leakThreshold,
      memoryRate,
      intervalGrowth,
      measurements
    };
  }
  
  // Start monitoring
  console.log('📈 Taking initial measurement...');
  initialMemory = takeMeasurement();
  
  console.log('Initial memory:', formatBytes(initialMemory.memory));
  console.log('Monitoring for 30 seconds...');
  
  // Take measurements every 5 seconds
  const intervals = [];
  for (let i = 1; i <= 6; i++) {
    intervals.push(setTimeout(() => {
      const measurement = takeMeasurement();
      console.log(`Measurement ${i}: ${formatBytes(measurement.memory)} memory`);
      
      if (i === 6) {
        analyzeMeasurements();
        console.log('\n💡 Tips to reduce memory usage:');
        console.log('- Close unused tabs');
        console.log('- Refresh the page if memory > 100MB');
        console.log('- Check for memory leaks in components');
        console.log('- Ensure proper cleanup in useEffect');
      }
    }, i * 5000));
  }
  
  // Return control object for manual testing
  return {
    measurements,
    takeMeasurement,
    analyzeMeasurements,
    formatBytes
  };
})();
