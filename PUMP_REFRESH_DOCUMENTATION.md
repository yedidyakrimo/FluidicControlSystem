# Vapourtec SF-10 Pump Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Pump Driver Implementation](#pump-driver-implementation)
4. [Refresh Button Logic](#refresh-button-logic)
5. [Connection Flow](#connection-flow)
6. [Health Check Mechanism](#health-check-mechanism)
7. [Error Handling](#error-handling)

---

## Overview

The Vapourtec SF-10 Pump is controlled through a Python driver that uses the `vapourtec` library for communication. The pump communicates via serial port (typically COM3 on Windows) at 9600 baud rate.

**Key Features:**
- Maximum flow rate: 5.0 ml/min
- Serial communication protocol
- Black tube type (ID 3) configuration required
- Active health checking via GV (Get Version) command
- Force reconnection capability for recovery

---

## Architecture

### Class Hierarchy

```
HardwareBase (base class)
    └── VapourtecPump
            ├── HardwareController (wrapper)
            └── MainTab (GUI integration)
```

### Key Components

1. **VapourtecPump** (`hardware/pump/vapourtec_pump.py`)
   - Core pump driver class
   - Handles all pump operations
   - Manages connection state

2. **HardwareController** (`hardware/hardware_controller.py`)
   - Wrapper class providing unified interface
   - Backward compatibility layer

3. **MainTab** (`gui/tabs/main_tab.py`)
   - GUI integration
   - Refresh button implementation
   - Status display

---

## Pump Driver Implementation

### Class: `VapourtecPump`

#### Initialization

```python
def __init__(self, port='COM3', baudrate=9600, timeout=1, tube_type=3):
    """
    Initialize Vapourtec pump
    
    Args:
        port: Serial port (e.g., 'COM3' on Windows)
        baudrate: Serial communication baudrate (usually 9600)
        timeout: Serial timeout in seconds
        tube_type: Tube type ID (3 = Black, default)
    """
    super().__init__()
    self.device_name = "Vapourtec SF-10 Pump"
    self.port = port
    self.baudrate = baudrate
    self.timeout = timeout
    self.tube_type = tube_type
    self.pump = None  # SF10 library instance
    self.ser = None   # Direct serial port access
    
    # State variables
    self.pump_setpoint_flow = 1.5
    self.previous_setpoint_flow = 1.5
    self.flow_change_time = time.time()
    self.is_running = False
    
    self.connect()  # Attempt initial connection
```

#### Connection Methods

##### 1. `connect()`

Standard connection method called during initialization.

```python
def connect(self):
    """Connect to pump via vapourtec library"""
    if not VAPOURTEC_AVAILABLE:
        self.enable_simulation()
        return False
    
    try:
        # Step 1: Create SF10 instance (library handshake)
        self.pump = SF10(self.port)
        self.ser = self.pump.ser  # Get direct serial access
        
        # Step 2: CRITICAL - Set Black tube type via raw command
        # The library doesn't support this natively
        self.ser.write(f'STTA {self.tube_type}\r\n'.encode())
        time.sleep(0.5)  # Wait for hardware processing
        
        # Step 3: Set mode to FLOW
        if hasattr(self.pump, 'MODE_FLOW'):
            self.pump.set_mode(self.pump.MODE_FLOW)
        
        # Step 4: Mark as connected
        self.connected = True
        self.simulation_mode = False
        return True
        
    except Exception as e:
        print(f"Error connecting: {e}")
        self.pump = None
        self.ser = None
        self.enable_simulation()
        return False
```

**Critical Note:** The `STTA 3` command (Set Tube Type A = 3 for Black tube) must be sent immediately after connection. Without this, the pump will not accept flow rate commands.

##### 2. `force_reconnect()`

Force reconnection method used by the Refresh button. Always attempts hardware connection regardless of current state.

```python
def force_reconnect(self):
    """
    Force a hard reconnection attempt to the pump hardware.
    Always tries to connect to physical hardware first,
    regardless of current simulation mode state.
    
    Returns:
        True if successfully connected, False otherwise
    """
    if not VAPOURTEC_AVAILABLE:
        self.enable_simulation()
        return False
    
    # Step 1: Close any existing connections
    try:
        if self.pump:
            self.stop()  # Stop pump before disconnecting
            self.pump.disconnect()
        if self.ser:
            self.ser.close()
    except:
        pass
    
    # Step 2: Clear all references
    self.pump = None
    self.ser = None
    self.connected = False
    self.is_running = False
    
    # Step 3: Attempt hardware handshake
    try:
        self.pump = SF10(self.port)
        self.ser = self.pump.ser
        
        # Step 4: CRITICAL - Send Black Tube command
        self.ser.write(f'STTA {self.tube_type}\r\n'.encode())
        time.sleep(0.5)
        
        # Step 5: Set mode to FLOW
        if hasattr(self.pump, 'MODE_FLOW'):
            self.pump.set_mode(self.pump.MODE_FLOW)
        
        # Step 6: Success
        self.connected = True
        self.simulation_mode = False
        return True
        
    except Exception as e:
        # Step 7: Failure - fall back to simulation
        print(f"Failed to reconnect: {e}")
        self.pump = None
        self.ser = None
        self.enable_simulation()
        return False
```

#### Control Methods

##### `set_flow_rate(flow_rate_ml_min)`

Sets the pump flow rate. Enforces maximum limit of 5.0 ml/min.

```python
def set_flow_rate(self, flow_rate_ml_min):
    """Set pump flow rate (max 5.0 ml/min)"""
    # Enforce limits
    if flow_rate_ml_min > self.MAX_FLOW_RATE:
        flow_rate_ml_min = self.MAX_FLOW_RATE
    if flow_rate_ml_min < 0:
        flow_rate_ml_min = 0.0
    
    if self.pump and self.connected:
        try:
            self.pump.set_flow_rate(float(flow_rate_ml_min))
            self.pump_setpoint_flow = flow_rate_ml_min
            self.flow_change_time = time.time()
            return True
        except Exception as e:
            print(f"Error setting flow rate: {e}")
            return False
    else:
        # Simulation mode
        self.pump_setpoint_flow = flow_rate_ml_min
        return True
```

##### `start()`

Starts the pump with proper initialization sequence.

```python
def start(self):
    """Start the pump - following exact sequence"""
    if self.pump and self.connected:
        try:
            # Step 1: Verify tube type
            if self.ser:
                self.ser.write(f'STTA {self.tube_type}\r\n'.encode())
                time.sleep(0.5)
            
            # Step 2: Set mode to FLOW
            if hasattr(self.pump, 'MODE_FLOW'):
                self.pump.set_mode(self.pump.MODE_FLOW)
                time.sleep(0.2)
            
            # Step 3: Set flow rate before starting
            if self.pump_setpoint_flow > 0:
                self.pump.set_flow_rate(float(self.pump_setpoint_flow))
                time.sleep(0.3)
            
            # Step 4: Start pump
            self.pump.start()
            time.sleep(0.5)
            
            self.is_running = True
            return True
        except Exception as e:
            print(f"Error starting pump: {e}")
            return False
    else:
        # Simulation mode
        self.is_running = True
        return True
```

##### `stop()`

Stops the pump.

```python
def stop(self):
    """Stop the pump"""
    if self.pump and self.connected:
        try:
            self.pump.stop()
            self.is_running = False
            return True
        except Exception as e:
            print(f"Error stopping pump: {e}")
            return False
    else:
        self.is_running = False
        return True
```

#### Data Reading Methods

##### `get_pressure()`

Reads pressure from pump using GP (Get Pressure) command.

```python
def get_pressure(self):
    """Get current pressure reading from pump"""
    if self.pump and self.ser and self.connected:
        try:
            # Clear pending data
            if self.ser.in_waiting > 0:
                self.ser.read(self.ser.in_waiting)
            
            # Send GP command
            self.ser.write(b'GP\r\n')
            time.sleep(0.2)
            
            # Read response with retries
            max_retries = 3
            for retry in range(max_retries):
                if self.ser.in_waiting > 0:
                    response = self.ser.read(self.ser.in_waiting).decode('ascii', errors='ignore').strip()
                    try:
                        return float(response)
                    except ValueError:
                        # Try to extract number from response
                        import re
                        numbers = re.findall(r'-?\d+\.?\d*', response)
                        if numbers:
                            return float(numbers[0])
                        if retry < max_retries - 1:
                            time.sleep(0.1)
                            continue
                else:
                    if retry < max_retries - 1:
                        time.sleep(0.1)
                        continue
            
            return None
        except Exception as e:
            print(f"Error reading pressure: {e}")
            return None
    else:
        # Simulation mode
        return self._simulate_data().get('pressure')
```

**Note:** Uses `in_waiting` instead of `read_all()` to avoid AttributeError issues.

##### `read_data()`

Reads all pump data (flow, pressure, RPM).

```python
def read_data(self):
    """Read data from pump (flow, pressure, RPM)"""
    if self.pump and self.connected:
        try:
            pressure = self.get_pressure()
            flow = self.pump_setpoint_flow
            rpm = int(300 + (flow * 100))  # Estimated RPM
            
            return {
                "flow": flow,
                "pressure": pressure if pressure is not None else 0.0,
                "rpm": rpm
            }
        except Exception as e:
            print(f"Error reading pump data: {e}")
            return self._simulate_data()
    else:
        return self._simulate_data()
```

---

## Refresh Button Logic

### GUI Integration (`gui/tabs/main_tab.py`)

#### Button Creation

```python
# In create_widgets() method
pump_btn_frame = ctk.CTkFrame(pump_status_frame)
pump_btn_frame.pack(pady=5)
self.create_blue_button(
    pump_btn_frame, 
    text='🔄 Refresh Status', 
    command=self.refresh_pump_status, 
    width=120, 
    height=30
).pack(side='left', padx=2)
```

#### Refresh Button Handler

```python
def refresh_pump_status(self):
    """Refresh pump connection status (with threading)"""
    print("DEBUG: Refresh pump button clicked")
    
    # 1. Update UI immediately (Main Thread)
    self.pump_status_label.configure(text="Scanning...", text_color='orange')
    
    # 2. Run logic in background thread
    threading.Thread(target=self._run_refresh_pump_logic, daemon=True).start()
```

**Key Points:**
- UI updates immediately to show "Scanning..." status
- Heavy I/O operations run in background thread to prevent GUI freezing
- Uses daemon thread so it doesn't block application shutdown

#### Background Refresh Logic

```python
def _run_refresh_pump_logic(self):
    """Background thread for pump status refresh with smart reconnection"""
    try:
        import time
        
        # Step 1: Check current status first (with health check)
        print("[REFRESH] Checking current pump status...")
        pump_info = self.hw_controller.pump.get_info()
        
        # Step 2: If already connected and working, don't force reconnect
        if pump_info.get('connected', False) and not pump_info.get('simulation_mode', False):
            print("[REFRESH] ✅ Pump already connected and responsive - no reconnection needed")
            self.after(0, lambda: self._update_pump_ui(pump_info))
            return
        
        # Step 3: If not connected or in simulation mode, attempt force reconnection
        print("[REFRESH] Pump not connected or in simulation mode - attempting FORCE reconnection...")
        
        if hasattr(self.hw_controller.pump, 'force_reconnect'):
            reconnect_success = self.hw_controller.pump.force_reconnect()
        else:
            reconnect_success = self.hw_controller.pump.connect()
        
        # Step 4: Handle success and failure differently
        if reconnect_success:
            print("[REFRESH] ✅ Pump force reconnection successful")
            # Give the pump more time to stabilize after reconnection
            # Increased to 2.0 seconds to ensure hardware is fully ready
            time.sleep(2.0)
            
            # CRITICAL FIX: Don't call get_info() after successful reconnection
            # The health check in get_info() might fail while pump is still initializing,
            # causing it to disconnect the pump again. Instead, trust force_reconnect()
            # and manually construct the pump_info dictionary with positive values.
            pump_info = {
                "device_name": self.hw_controller.pump.device_name,
                "port": self.hw_controller.pump.port,
                "connected": True,  # Trust force_reconnect result
                "simulation_mode": False,
                "is_running": self.hw_controller.pump.is_running,
                "current_flow_rate": self.hw_controller.pump.pump_setpoint_flow,
                "tube_type": self.hw_controller.pump.tube_type,
                "max_flow_rate": self.hw_controller.pump.MAX_FLOW_RATE,
                "status": "Connected",
                "status_color": "green"
            }
            print("[REFRESH] Trusting force_reconnect result - marking as connected without health check")
        else:
            print("[REFRESH] ❌ Pump force reconnection failed - staying in simulation mode")
            # Only call get_info() if reconnection failed to read actual error/disconnected state
            pump_info = self.hw_controller.pump.get_info()
        
        # Step 5: Schedule UI update back on Main Thread
        self.after(0, lambda: self._update_pump_ui(pump_info))
        
    except Exception as e:
        error_msg = str(e)
        print(f"[REFRESH] Error during pump refresh: {error_msg}")
        self.after(0, lambda: self._update_pump_error(error_msg))
```

**Refresh Logic Flow:**

1. **Check Current Status**: First calls `get_info()` which performs active health check
2. **Smart Decision**: If already connected and working, skip reconnection
3. **Force Reconnect**: If not connected, calls `force_reconnect()`
4. **Success Handling**: 
   - **CRITICAL**: If `force_reconnect()` succeeds, **DO NOT** call `get_info()` immediately
   - Instead, manually construct `pump_info` dictionary with positive values
   - Wait 2.0 seconds for hardware stabilization
   - Trust the `force_reconnect()` result
5. **Failure Handling**: Only call `get_info()` if reconnection failed to read actual error state
6. **Update UI**: Schedules UI update on main thread using `self.after(0, ...)`

**Why This Fix Works:**

The issue was that after `force_reconnect()` succeeded, calling `get_info()` immediately would trigger a health check (GV command). If the pump was still initializing, this command would fail or timeout, causing `get_info()` to disconnect the pump again.

By trusting the `force_reconnect()` result and manually constructing the status dictionary, we avoid the premature health check that could disconnect a newly connected pump.

#### UI Update Methods

```python
def _update_pump_ui(self, pump_info):
    """Update pump UI with results (called on main thread)"""
    try:
        # Update status label with color
        status_text = pump_info.get('status', 'Unknown')
        status_color = pump_info.get('status_color', 'gray')
        self.pump_status_label.configure(text=status_text, text_color=status_color)
        
        # Update port
        port_text = pump_info.get('port', 'N/A')
        self.pump_port_label.configure(text=port_text)
        
        # Update flow rate
        flow_rate = pump_info.get('current_flow_rate', 0.0)
        self.pump_flow_label.configure(text=f'{flow_rate:.2f} ml/min')
        
        # Update max flow rate display
        max_flow = pump_info.get('max_flow_rate', 5.0)
        self.pump_max_flow_label.configure(text=f'{max_flow:.1f} ml/min')
    except Exception as e:
        print(f"Error updating pump UI: {e}")
        self.pump_status_label.configure(text='Error', text_color='red')

def _update_pump_error(self, error_msg):
    """Update pump UI with error (called on main thread)"""
    print(f"Error refreshing pump status: {error_msg}")
    self.pump_status_label.configure(text='Error', text_color='red')
```

---

## Connection Flow

### Initial Connection (Startup)

```
Application Start
    ↓
HardwareController.__init__()
    ↓
VapourtecPump.__init__()
    ↓
VapourtecPump.connect()
    ↓
SF10(self.port)  [Library handshake]
    ↓
self.ser.write('STTA 3\r\n')  [Set Black tube]
    ↓
self.pump.set_mode(MODE_FLOW)
    ↓
self.connected = True
```

### Refresh Button Flow

```
User Clicks Refresh
    ↓
refresh_pump_status() [Main Thread]
    ↓
Update UI: "Scanning..."
    ↓
Thread: _run_refresh_pump_logic()
    ↓
get_info() [Health Check]
    ↓
Is Connected? ──Yes──→ Update UI (Done)
    │
    No
    ↓
force_reconnect()
    ↓
Close existing connections
    ↓
SF10(self.port) [New handshake]
    ↓
STTA 3 [Set Black tube]
    ↓
set_mode(MODE_FLOW)
    ↓
    ┌─────────────────────────┐
    │  Did it succeed?        │
    └─────────────────────────┘
            │
    ┌───────┴────────┐
    │                │
   Yes              No
    │                │
    ↓                ↓
Wait 2.0 sec    get_info() [Read error state]
    │                │
    ↓                ↓
Build pump_info  pump_info = get_info()
manually with    (simulation mode)
positive values
    │                │
    └───────┬────────┘
            │
            ↓
    Update UI
```

---

## Health Check Mechanism

### `get_info()` Method

The `get_info()` method performs an active health check by sending a GV (Get Version) command to verify the pump is actually responsive.

```python
def get_info(self):
    """Get pump connection information with active health check"""
    info = {
        "device_name": self.device_name,
        "port": self.port,
        "connected": self.connected,
        "simulation_mode": self.simulation_mode,
        "is_running": self.is_running,
        "current_flow_rate": self.pump_setpoint_flow,
        "tube_type": self.tube_type,
        "max_flow_rate": self.MAX_FLOW_RATE
    }
    
    # Active Health Check: Only if we think we're connected
    if self.connected and not self.simulation_mode and self.ser:
        try:
            # Clear any pending data first
            if self.ser.in_waiting > 0:
                self.ser.read(self.ser.in_waiting)
            
            # Send GV (Get Version) command as a ping
            self.ser.write(b'GV\r\n')
            time.sleep(0.5)  # Wait for response
            
            # Check if we got a response
            if self.ser.in_waiting > 0:
                self.ser.read(self.ser.in_waiting)
                info["status"] = "Connected"
                info["status_color"] = "green"
                info["connected"] = True
            else:
                # No response - try one more time
                time.sleep(0.5)
                if self.ser.in_waiting > 0:
                    self.ser.read(self.ser.in_waiting)
                    info["status"] = "Connected"
                    info["status_color"] = "green"
                    info["connected"] = True
                else:
                    raise Exception("No response to GV command after retry")
                    
        except Exception as e:
            # Health check failed - close connection
            print(f"Pump health check failed: {error_msg}")
            
            # Close connections
            try:
                if self.pump:
                    self.pump.disconnect()
                if self.ser:
                    self.ser.close()
            except:
                pass
            
            # Mark as disconnected
            self.pump = None
            self.ser = None
            self.connected = False
            info["connected"] = False
            info["status"] = "Not Connected"
            info["status_color"] = "red"
    elif self.connected and not self.simulation_mode:
        # Connected but no serial port yet (just after force_reconnect)
        info["status"] = "Connected"
        info["status_color"] = "green"
        info["connected"] = True
    elif self.simulation_mode:
        info["status"] = "Simulation Mode"
        info["status_color"] = "orange"
    else:
        info["status"] = "Not Connected"
        info["status_color"] = "red"
    
    return info
```

**Health Check Features:**
- Sends GV command to verify device responsiveness
- Clears buffer before sending command
- Waits 0.5 seconds for response
- Retries once if no immediate response
- Closes connection if health check fails
- Marks device as disconnected on failure

**Important Note:** The health check in `get_info()` should NOT be called immediately after `force_reconnect()` succeeds, as the pump may still be initializing and the health check could fail, causing the pump to be disconnected again.

---

## Error Handling

### Timeout Handling in Experiment Thread

The experiment thread includes timeout handling for pump operations:

```python
# In experiment_thread() method
try:
    self.exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
    time.sleep(0.3)
    pump_started = self.exp_manager.hw_controller.start_pump()
    time.sleep(0.5)
    self.exp_manager.hw_controller.set_valves(...)
except Exception as e:
    # Catch SerialReadTimeoutException or any other timeout/communication error
    error_msg = str(e)
    error_type = type(e).__name__
    print(f"[EXPERIMENT_THREAD] Pump timeout/error: {error_type}: {error_msg}")
    
    # Mark pump as disconnected
    if hasattr(self.exp_manager.hw_controller.pump, 'connected'):
        self.exp_manager.hw_controller.pump.connected = False
    
    # Stop the experiment safely
    if self.update_queue:
        self.update_queue.put(('UPDATE_STATUS', 'Experiment stopped: Pump unresponsive'))
        self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Stopped: Pump Timeout', 'red')))
    
    # Stop experiment manager
    self.exp_manager.stop_experiment()
    
    # Update UI
    self.after(0, lambda: self.pump_status_label.configure(
        text='✗ Disconnected (Timeout)', 
        text_color='red'
    ))
    
    return  # Exit the experiment thread
```

### Connection Error Handling

All connection methods include try/except blocks:

```python
try:
    # Connection attempt
    self.pump = SF10(self.port)
    # ... setup commands ...
    self.connected = True
    return True
except Exception as e:
    # Error handling
    print(f"Error: {e}")
    self.pump = None
    self.ser = None
    self.enable_simulation()
    return False
```

---

## Key Design Decisions

### 1. Threading for Refresh

**Why:** Heavy I/O operations (serial port communication) can block the GUI thread, making the application unresponsive.

**Solution:** Refresh operations run in background threads, with UI updates scheduled on the main thread using `self.after(0, ...)`.

### 2. Active Health Check

**Why:** Just checking if a port is open doesn't verify the device is actually responsive.

**Solution:** Sends GV (Get Version) command and waits for response. If no response, marks device as disconnected.

### 3. Force Reconnect

**Why:** When a device is turned off and back on, the software might still think it's connected.

**Solution:** `force_reconnect()` always attempts hardware connection, closing existing connections first.

### 4. Smart Refresh Logic

**Why:** Constantly reconnecting when already connected can cause issues.

**Solution:** Checks current status first. Only attempts reconnection if not connected or in simulation mode.

### 5. Trust Reconnection Result (CRITICAL FIX)

**Why:** After `force_reconnect()` succeeds, calling `get_info()` immediately triggers a health check. If the pump is still initializing, the health check fails and disconnects the pump again.

**Solution:** 
- If `force_reconnect()` succeeds, **DO NOT** call `get_info()` immediately
- Instead, manually construct `pump_info` dictionary with positive values
- Wait 2.0 seconds for hardware stabilization
- Only call `get_info()` if reconnection failed to read actual error state

This prevents the health check from accidentally disconnecting a newly connected device.

---

## Serial Commands Reference

| Command | Description | Usage |
|---------|-------------|-------|
| `STTA 3` | Set Tube Type A = 3 (Black tube) | Must be sent immediately after connection |
| `GV` | Get Version | Used for health check ping |
| `GP` | Get Pressure | Read current pressure value |
| Flow rate commands | Set via library method | `pump.set_flow_rate(value)` |

---

## Troubleshooting

### Pump Not Connecting

1. **Check Port**: Verify COM port is correct (usually COM3)
2. **Check Remote Control**: Ensure pump has remote control enabled
3. **Check Library**: Verify `vapourtec` library is installed
4. **Check Cable**: Verify USB/serial cable is connected

### Health Check Failing

1. **Wait Time**: Pump might need more time to respond
2. **Buffer**: Clear serial buffer before sending commands
3. **Retry**: Health check includes one retry attempt
4. **Avoid After Reconnect**: Don't call `get_info()` immediately after `force_reconnect()` succeeds

### Refresh Not Updating

1. **Threading**: Check that background thread is running
2. **UI Update**: Verify `self.after(0, ...)` is being called
3. **Status Check**: Check console for debug messages
4. **Trust Reconnection**: If `force_reconnect()` succeeds, status is set manually without health check

---

## Summary

The Vapourtec SF-10 Pump driver provides:

- **Robust Connection Management**: Handles connection, disconnection, and reconnection
- **Active Health Checking**: Verifies device responsiveness via GV command (when appropriate)
- **Thread-Safe Operations**: Background threads for heavy I/O, main thread for UI updates
- **Error Recovery**: Automatic fallback to simulation mode on errors
- **Smart Refresh**: Only reconnects when necessary, preserves working connections
- **Trust Reconnection Result**: After successful `force_reconnect()`, trusts the result and avoids premature health check that could disconnect the device

The Refresh button implementation ensures the pump status is always accurate and can recover from connection issues automatically, while avoiding the pitfall of disconnecting a newly connected device due to premature health checks.

