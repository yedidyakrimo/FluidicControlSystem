# Main Tab Button Layout and Design Documentation

## Overview

The Main Tab (`main_tab.py`) is the primary interface for experiment control and real-time monitoring in the Fluidic Control System. This document provides a comprehensive guide to the button layout, widget organization, and design patterns used in this tab.

## Table of Contents

1. [Overall Structure](#overall-structure)
2. [Left Panel Layout](#left-panel-layout)
3. [Button Design and Styling](#button-design-and-styling)
4. [Control Buttons Section](#control-buttons-section)
5. [Code Examples](#code-examples)
6. [Design Patterns](#design-patterns)

---

## Overall Structure

The Main Tab uses a **horizontal PanedWindow** layout that divides the interface into two resizable sections:

```python
# Create PanedWindow for resizable panels
paned = PanedWindow(self, orient='horizontal', sashwidth=8, sashrelief='raised', bg='#2b2b2b')
paned.pack(fill='both', expand=True, padx=5, pady=5)
```

### Layout Components:
- **Left Panel**: Scrollable control panel (width: 400px, minimum: 250px)
- **Right Panel**: Graph visualization area (minimum: 400px)

---

## Left Panel Layout

The left panel is organized as a **CTkScrollableFrame** containing multiple sections stacked vertically:

### Section Order (Top to Bottom):

1. **Pump Connection Status**
2. **Experiment Parameters**
3. **Experiment Metadata**
4. **Control Buttons** ⭐ (Main focus of this document)
5. **Current Readings**
6. **Real-Time Statistics**
7. **Recording Status**
8. **Keithley 2450 SMU Control**

Each section is wrapped in a `CTkFrame` with consistent padding (`pady=5`).

---

## Control Buttons Section

The **Control** section (lines 163-200) contains the primary experiment control buttons and export functionality.

### Section Header
```python
control_frame = ctk.CTkFrame(left_frame)
control_frame.pack(fill='x', pady=5)
ctk.CTkLabel(control_frame, text="Control", font=('Helvetica', 14, 'bold')).pack(pady=5)
```

### Button Layout Structure

#### 1. Primary Control Buttons (Vertical Stack)

All primary buttons use the `create_blue_button()` method and are stacked vertically with `pady=2` spacing:

```python
# Start Recording Button
self.start_btn = self.create_blue_button(control_frame, text='Start Recording',
                                         command=self.start_recording, width=150, height=40)
self.start_btn.pack(pady=2)

# Stop Recording Button
self.stop_btn = self.create_blue_button(control_frame, text='Stop Recording',
                                        command=self.stop_recording, width=150, height=40,
                                        fg_color='#0D47A1', hover_color='#0C3A7A')
self.stop_btn.pack(pady=2)

# Finish Recording Button
self.finish_btn = self.create_blue_button(control_frame, text='Finish Recording',
                                          command=self.finish_recording, width=150, height=40,
                                          fg_color='#0C6CC0', hover_color='#0A518A')
self.finish_btn.pack(pady=2)

# Update Flow Button
self.update_flow_btn = self.create_blue_button(control_frame, text='Update Flow',
                                              command=self.update_flow, width=150)
self.update_flow_btn.pack(pady=2)

# Clear Graph Button
self.clear_graph_btn = self.create_blue_button(control_frame, text='Clear Graph',
                                               command=self.clear_graph, width=150)
self.clear_graph_btn.pack(pady=2)
```

**Button Specifications:**
- **Width**: 150px (consistent for all primary buttons)
- **Height**: 40px (for Start/Stop/Finish), default for others
- **Spacing**: 2px vertical padding between buttons
- **Alignment**: Centered (default pack behavior)

#### 2. Export Menu (Horizontal Layout)

The export section uses a horizontal frame with a label and three export buttons:

```python
export_menu_frame = ctk.CTkFrame(control_frame)
export_menu_frame.pack(pady=2)

# Export Label
ctk.CTkLabel(export_menu_frame, text='Export:', width=80).pack(side='left', padx=5)

# Excel Export Button
self.export_btn = self.create_blue_button(export_menu_frame, text='Excel',
                                         command=self.export_excel, width=100)
self.export_btn.pack(side='left', padx=2)

# PNG Export Button
self.create_blue_button(export_menu_frame, text='PNG', 
                       command=self.export_graph_png, width=100).pack(side='left', padx=2)

# PDF Export Button
self.create_blue_button(export_menu_frame, text='PDF', 
                       command=self.export_graph_pdf, width=100).pack(side='left', padx=2)
```

**Export Menu Specifications:**
- **Layout**: Horizontal (`side='left'`)
- **Label Width**: 80px
- **Button Width**: 100px each
- **Horizontal Spacing**: 5px (label), 2px (between buttons)

---

## Button Design and Styling

### Custom Blue Button Method

The Main Tab inherits from `BaseTab`, which provides the `create_blue_button()` method. This method creates consistently styled buttons with a blue color scheme.

**Default Button Properties:**
- **Base Color**: Custom blue (likely `#1976D2` or similar)
- **Hover Color**: Darker blue variant
- **Text Color**: White
- **Font**: System default (typically Helvetica)

### Button Color Variations

Different buttons use different shades to indicate their function:

| Button | fg_color | hover_color | Purpose |
|--------|----------|-------------|---------|
| Start Recording | Default blue | Default hover | Primary action |
| Stop Recording | `#0D47A1` (darker) | `#0C3A7A` | Warning/stop action |
| Finish Recording | `#0C6CC0` (medium) | `#0A518A` | Completion action |
| Update Flow | Default blue | Default hover | Secondary action |
| Clear Graph | Default blue | Default hover | Utility action |
| Export buttons | Default blue | Default hover | Export actions |

### Button Dimensions

```
Primary Control Buttons:
├── Start/Stop/Finish: 150px × 40px
├── Update Flow: 150px × default height
└── Clear Graph: 150px × default height

Export Buttons:
└── Excel/PNG/PDF: 100px × default height
```

---

## Additional Control Elements

### Pump Status Refresh Button

Located in the **Pump Connection Status** section:

```python
pump_btn_frame = ctk.CTkFrame(pump_status_frame)
pump_btn_frame.pack(pady=5)
self.create_blue_button(pump_btn_frame, text='🔄 Refresh Status', 
                       command=self.refresh_pump_status, width=120, height=30).pack(side='left', padx=2)
```

**Specifications:**
- **Width**: 120px
- **Height**: 30px
- **Icon**: 🔄 (refresh emoji)
- **Layout**: Horizontal frame (allows for future expansion)

### Keithley SMU Refresh Button

Located in the **Keithley 2450 SMU Control** section:

```python
smu_btn_frame = ctk.CTkFrame(keithley_frame)
smu_btn_frame.pack(pady=5)
self.create_blue_button(smu_btn_frame, text='🔄 Refresh SMU Status', 
                       command=self.refresh_keithley_status, width=150, height=30).pack(side='left', padx=2)
```

**Specifications:**
- **Width**: 150px
- **Height**: 30px
- **Icon**: 🔄 (refresh emoji)

---

## Code Examples

### Complete Control Section Code

```python
# Control buttons
control_frame = ctk.CTkFrame(left_frame)
control_frame.pack(fill='x', pady=5)
ctk.CTkLabel(control_frame, text="Control", font=('Helvetica', 14, 'bold')).pack(pady=5)

# Primary control buttons (vertical stack)
self.start_btn = self.create_blue_button(control_frame, text='Start Recording',
                                         command=self.start_recording, width=150, height=40)
self.start_btn.pack(pady=2)

self.stop_btn = self.create_blue_button(control_frame, text='Stop Recording',
                                        command=self.stop_recording, width=150, height=40,
                                        fg_color='#0D47A1', hover_color='#0C3A7A')
self.stop_btn.pack(pady=2)

self.finish_btn = self.create_blue_button(control_frame, text='Finish Recording',
                                          command=self.finish_recording, width=150, height=40,
                                          fg_color='#0C6CC0', hover_color='#0A518A')
self.finish_btn.pack(pady=2)

self.update_flow_btn = self.create_blue_button(control_frame, text='Update Flow',
                                              command=self.update_flow, width=150)
self.update_flow_btn.pack(pady=2)

self.clear_graph_btn = self.create_blue_button(control_frame, text='Clear Graph',
                                               command=self.clear_graph, width=150)
self.clear_graph_btn.pack(pady=2)

# Export menu (horizontal layout)
export_menu_frame = ctk.CTkFrame(control_frame)
export_menu_frame.pack(pady=2)

ctk.CTkLabel(export_menu_frame, text='Export:', width=80).pack(side='left', padx=5)
self.export_btn = self.create_blue_button(export_menu_frame, text='Excel',
                                         command=self.export_excel, width=100)
self.export_btn.pack(side='left', padx=2)

self.create_blue_button(export_menu_frame, text='PNG', 
                       command=self.export_graph_png, width=100).pack(side='left', padx=2)

self.create_blue_button(export_menu_frame, text='PDF', 
                       command=self.export_graph_pdf, width=100).pack(side='left', padx=2)
```

### Creating a Custom Button

To add a new button following the same design pattern:

```python
# Example: Add a "Pause" button
self.pause_btn = self.create_blue_button(
    control_frame, 
    text='Pause Recording',
    command=self.pause_recording, 
    width=150, 
    height=40,
    fg_color='#FF9800',  # Orange for pause
    hover_color='#F57C00'
)
self.pause_btn.pack(pady=2)
```

---

## Design Patterns

### 1. Consistent Spacing

- **Section Padding**: `pady=5` between major sections
- **Button Spacing**: `pady=2` between primary buttons
- **Horizontal Spacing**: `padx=2` or `padx=5` for horizontal elements

### 2. Frame Hierarchy

```
left_frame (CTkScrollableFrame)
└── control_frame (CTkFrame)
    ├── Label: "Control"
    ├── start_btn (packed with pady=2)
    ├── stop_btn (packed with pady=2)
    ├── finish_btn (packed with pady=2)
    ├── update_flow_btn (packed with pady=2)
    ├── clear_graph_btn (packed with pady=2)
    └── export_menu_frame (CTkFrame)
        ├── Label: "Export:"
        ├── Excel button (side='left', padx=2)
        ├── PNG button (side='left', padx=2)
        └── PDF button (side='left', padx=2)
```

### 3. Color Coding Strategy

- **Primary Actions** (Start): Default blue
- **Warning Actions** (Stop): Darker blue (`#0D47A1`)
- **Completion Actions** (Finish): Medium blue (`#0C6CC0`)
- **Utility Actions** (Update, Clear, Export): Default blue

### 4. Button Size Hierarchy

- **Large Primary Buttons**: 150px × 40px (Start/Stop/Finish)
- **Standard Buttons**: 150px × default (Update/Clear)
- **Compact Buttons**: 100px × default (Export)
- **Small Buttons**: 120-150px × 30px (Refresh buttons)

### 5. Responsive Layout

- **Left Panel**: Scrollable (handles overflow)
- **Minimum Width**: 250px (prevents UI breaking)
- **Preferred Width**: 400px
- **Buttons**: Fixed width (prevents layout shifts)

---

## Visual Layout Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    MAIN TAB INTERFACE                   │
├──────────────────────────┬──────────────────────────────┤
│   LEFT PANEL (400px)     │   RIGHT PANEL (Graphs)       │
│   ┌──────────────────┐   │                              │
│   │ Pump Status      │   │                              │
│   │ [🔄 Refresh]     │   │                              │
│   ├──────────────────┤   │                              │
│   │ Experiment Params│   │                              │
│   ├──────────────────┤   │                              │
│   │ Metadata         │   │                              │
│   ├──────────────────┤   │                              │
│   │ CONTROL          │   │                              │
│   │ ┌──────────────┐ │   │                              │
│   │ │[Start Record]│ │   │                              │
│   │ │[Stop Record] │ │   │                              │
│   │ │[Finish Record]│ │   │                              │
│   │ │[Update Flow]  │ │   │                              │
│   │ │[Clear Graph]  │ │   │                              │
│   │ └──────────────┘ │   │                              │
│   │ Export: [Excel]  │   │                              │
│   │         [PNG][PDF]│   │                              │
│   ├──────────────────┤   │                              │
│   │ Current Readings │   │                              │
│   ├──────────────────┤   │                              │
│   │ Statistics       │   │                              │
│   ├──────────────────┤   │                              │
│   │ Recording Status │   │                              │
│   ├──────────────────┤   │                              │
│   │ Keithley Control │   │                              │
│   │ [🔄 Refresh SMU] │   │                              │
│   └──────────────────┘   │                              │
└──────────────────────────┴──────────────────────────────┘
```

---

## Button Function Reference

| Button | Method | Purpose |
|--------|--------|---------|
| Start Recording | `start_recording()` | Begin experiment data collection |
| Stop Recording | `stop_recording()` | Pause experiment (preserves data) |
| Finish Recording | `finish_recording()` | Complete experiment gracefully |
| Update Flow | `update_flow()` | Change flow rate during experiment |
| Clear Graph | `clear_graph()` | Clear all graph data and reset timer |
| Excel Export | `export_excel()` | Export data to Excel file |
| PNG Export | `export_graph_png()` | Export current graph as PNG |
| PDF Export | `export_graph_pdf()` | Export current graph as PDF |
| Refresh Status | `refresh_pump_status()` | Reconnect/refresh pump connection |
| Refresh SMU | `refresh_keithley_status()` | Reconnect/refresh SMU connection |

---

## Styling Details

### CustomTkinter Theme

The application uses **CustomTkinter** (CTk) widgets which provide:
- Modern, flat design
- Dark theme support (default)
- Consistent styling across widgets
- Customizable colors

### Color Palette

Based on the code analysis:

- **Background**: `#1a1a1a` (dark gray for frames)
- **PanedWindow**: `#2b2b2b` (slightly lighter gray)
- **Button Default**: Blue (CustomTkinter default)
- **Button Stop**: `#0D47A1` (dark blue)
- **Button Finish**: `#0C6CC0` (medium blue)
- **Text Labels**: White (default)
- **Gray Text**: `gray` (for hints/help text)

### Typography

- **Section Headers**: `('Helvetica', 14, 'bold')`
- **Subsection Headers**: `('Helvetica', 12, 'bold')`
- **Labels**: Default font
- **Help Text**: `('Helvetica', 9)` with gray color

---

## Best Practices

1. **Consistent Button Sizing**: Use 150px width for primary actions, 100px for secondary
2. **Color Coding**: Use darker shades for warning/stop actions
3. **Vertical Stacking**: Primary buttons should be stacked vertically for clarity
4. **Horizontal Grouping**: Related actions (like exports) should be grouped horizontally
5. **Spacing**: Maintain consistent `pady=2` for button spacing, `pady=5` for sections
6. **Frame Nesting**: Use frames to group related buttons and maintain layout structure

---

## Conclusion

The Main Tab button layout follows a clear hierarchical structure with consistent styling and spacing. The Control section serves as the primary interface for experiment management, with buttons organized by function and importance. The design emphasizes usability through color coding, size hierarchy, and logical grouping of related actions.

