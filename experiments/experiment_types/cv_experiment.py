"""
Cyclic Voltammetry (CV) experiment type using SCPI commands
"""

import time
from experiments.base_experiment import BaseExperiment
from utils.logger_config import get_logger

logger = get_logger(__name__)


class CVExperiment(BaseExperiment):
    """
    Cyclic Voltammetry experiment using SCPI commands (command-by-command)
    Performs 4-vertex sweep: V1 -> V2 -> V3 -> V4 -> V1
    Similar to iv_tab.py pattern but with cyclic sweep logic
    """
    
    def __init__(self, hardware_controller, data_handler):
        """
        Initialize CV experiment
        
        Args:
            hardware_controller: HardwareController instance
            data_handler: DataHandler instance
        """
        super().__init__(hardware_controller, data_handler)
        # Store data for GUI access
        self.voltage_data = []
        self.current_data = []
    
    def _calculate_sweep_parameters(self, v1, v2, v3, v4, points_per_second):
        """
        Calculate sweep parameters (same logic as TSP version)
        
        Args:
            v1, v2, v3, v4: Voltage vertices (V)
            points_per_second: Sampling density (points/sec)
        
        Returns:
            dict with: points_per_segment, step_sizes, dwell_time, vertices
        """
        # Calculate total path length
        path_segments = [
            abs(v2 - v1),  # V1 -> V2
            abs(v3 - v2),  # V2 -> V3
            abs(v4 - v3),  # V3 -> V4
            abs(v1 - v4)   # V4 -> V1
        ]
        total_path_length = sum(path_segments)
        
        # Calculate total number of points
        # Estimate time: total_path_length / average_sweep_rate
        # For CV, assume average sweep rate of 1 V/s (can be adjusted)
        estimated_time = total_path_length / 1.0  # seconds
        total_points = int(points_per_second * estimated_time)
        
        # Ensure minimum points per segment
        min_points_per_segment = 10
        total_points = max(total_points, min_points_per_segment * 4)
        
        # Calculate points per segment (proportional to segment length)
        points_per_segment = []
        for segment_length in path_segments:
            if total_path_length > 0:
                points = max(min_points_per_segment, 
                            int(total_points * (segment_length / total_path_length)))
            else:
                points = min_points_per_segment
            points_per_segment.append(points)
        
        # Calculate step sizes for each segment
        step_sizes = []
        for i, (segment_length, points) in enumerate(zip(path_segments, points_per_segment)):
            if points > 1:
                step = segment_length / (points - 1)
            else:
                step = 0.0
            step_sizes.append(step)
        
        # Calculate dwell time (time per point)
        dwell_time = 1.0 / points_per_second  # seconds
        
        # Vertices for sweep
        vertices = [v1, v2, v3, v4, v1]  # Include return to V1
        
        return {
            'points_per_segment': points_per_segment,
            'step_sizes': step_sizes,
            'dwell_time': dwell_time,
            'vertices': vertices,
            'path_segments': path_segments
        }
    
    def _setup_smu_for_cv(self, current_range, current_limit=0.1):
        """
        Setup SMU for CV measurement (Source Voltage, Measure Current)
        
        Args:
            current_range: Manual current range (A)
            current_limit: Current limit/compliance (A)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.hw_controller or not self.hw_controller.smu:
            logger.warning("SMU not connected - setup skipped")
            return False
        
        try:
            smu = self.hw_controller.smu
            
            # Use existing setup_for_iv_measurement for basic configuration
            if not smu.setup_for_iv_measurement(current_limit):
                return False
            
            # Override with manual current range (not auto)
            logger.debug(f"Sending: SENS:CURR:RANG {current_range}")
            smu.smu.write(smu.scpi.set_current_range(current_range))
            time.sleep(0.1)
            
            logger.info("SMU Setup Complete for CV: Source V, Measure I (Manual Range)")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up SMU for CV: {e}", exc_info=True)
            return False
    
    def run(self, v1, v2, v3, v4, points_per_second, current_range, current_limit=0.1):
        """
        Run CV experiment using SCPI commands
        
        Args:
            v1, v2, v3, v4: Voltage vertices (V)
            points_per_second: Sampling density (points/sec)
            current_range: Manual current range (A)
            current_limit: Current limit/compliance (A), default 0.1
        """
        if not self.is_running:
            self.is_running = True
            logger.info("Starting CV measurement...")
        
        # Clear previous data
        self.voltage_data = []
        self.current_data = []
        
        try:
            # Check SMU connection
            if not self.hw_controller or not self.hw_controller.smu or not self.hw_controller.smu.connected:
                logger.warning("SMU not connected - CV measurement cancelled")
                self.stop()
                return
            
            # Create new data file
            self.data_handler.create_new_file()
            
            # Setup SMU
            logger.info(f"Setting up SMU for CV: Current range={current_range}A, Current limit={current_limit}A")
            if not self._setup_smu_for_cv(current_range, current_limit):
                logger.error("Failed to setup SMU")
                self.stop()
                return
            
            # Calculate sweep parameters
            params = self._calculate_sweep_parameters(v1, v2, v3, v4, points_per_second)
            points_per_segment = params['points_per_segment']
            step_sizes = params['step_sizes']
            dwell_time = params['dwell_time']
            vertices = params['vertices']
            
            logger.info(f"Running CV sweep: V1={v1}V, V2={v2}V, V3={v3}V, V4={v4}V")
            logger.debug(f"Points per second: {points_per_second}, Current range: {current_range}A")
            logger.debug(f"Dwell time: {dwell_time:.4f}s per point")
            
            # Execute sweep: V1 -> V2 -> V3 -> V4 -> V1
            segment_names = ["V1->V2", "V2->V3", "V3->V4", "V4->V1"]
            
            for seg_idx, (start_v, end_v, step_size, points, seg_name) in enumerate(
                zip(vertices[:-1], vertices[1:], step_sizes, points_per_segment, segment_names)
            ):
                if not self.is_running:
                    logger.info("CV sweep stopped by user")
                    break
                
                logger.debug(f"Segment {seg_idx + 1}: {seg_name} ({points} points)")
                
                if abs(end_v - start_v) < 1e-9:  # Very small difference
                    # Single point
                    voltage = end_v
                    self.hw_controller.set_smu_voltage(voltage, current_limit)
                    time.sleep(dwell_time)
                    measurement = self.hw_controller.measure_smu(mode="voltage")
                    if measurement:
                        self.voltage_data.append(measurement.get('voltage', voltage))
                        self.current_data.append(measurement.get('current', 0.0))
                else:
                    # Sweep segment
                    direction = 1 if end_v > start_v else -1
                    
                    for i in range(points):
                        if not self.is_running:
                            logger.info("CV sweep stopped by user")
                            break
                        
                        # Calculate voltage for this point
                        if points > 1:
                            voltage = start_v + i * step_size * direction
                        else:
                            voltage = end_v
                        
                        # Set voltage
                        self.hw_controller.set_smu_voltage(voltage, current_limit)
                        
                        # Wait for dwell time
                        time.sleep(dwell_time)
                        
                        # Measure
                        measurement = self.hw_controller.measure_smu(mode="voltage")
                        if measurement:
                            measured_voltage = measurement.get('voltage', voltage)
                            measured_current = measurement.get('current', 0.0)
                            
                            # Store data
                            self.voltage_data.append(measured_voltage)
                            self.current_data.append(measured_current)
                            
                            # Save to data handler
                            data_point = {
                                "time": len(self.voltage_data) - 1,
                                "voltage": measured_voltage,
                                "current": measured_current,
                                "elapsed_time": (len(self.voltage_data) - 1) / points_per_second if points_per_second > 0 else 0
                            }
                            self.data_handler.append_data(data_point)
                        else:
                            logger.warning(f"Failed to measure at {voltage:.4f}V")
            
            # Turn output OFF after sweep
            if self.hw_controller.smu and self.hw_controller.smu.connected:
                try:
                    self.hw_controller.smu.smu.write(self.hw_controller.smu.scpi.output_off())
                    logger.debug("Output turned OFF")
                except Exception as e:
                    logger.warning(f"Could not turn output OFF: {e}")
            
            logger.info(f"CV measurement completed: {len(self.voltage_data)} data points")
            
        except Exception as e:
            logger.error(f"Error in CV experiment: {e}", exc_info=True)
        finally:
            self.stop()
            logger.info("CV measurement finished.")

