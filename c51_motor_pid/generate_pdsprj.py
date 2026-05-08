# -*- coding: utf-8 -*-
"""
=============================================================================
Proteus 8.x Project File (.pdsprj) Generator for C51 Motor PID
=============================================================================
This script programmatically generates a valid Proteus 8 project file.
Proteus 8 files are zip archives containing project configuration and 
schematic XML definitions.
=============================================================================
"""

import os
import zipfile

def create_pdsprj():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(project_dir, "c51_motor_pid.pdsprj")
    
    print("[Proteus Gen] Generating XML files for Proteus 8...")
    
    # 1. project.xml
    project_xml = """<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<PROJECT NAME="c51_motor_pid" VERSION="1.0">
  <MODULE NAME="ISIS" TYPE="SCHEMATIC">
    <FILE NAME="schematic.xml"/>
  </MODULE>
</PROJECT>
"""

    # 2. metainfo.xml
    metainfo_xml = """<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<METAINFO>
  <AUTHOR>C51 PID Homework Team</AUTHOR>
  <DESCRIPTION>AT89C51 DC Motor Speed Closed-Loop PID Control System Simulation Project.</DESCRIPTION>
  <CREATED>2026-05-08</CREATED>
  <TOOL>Proteus 8 Professional</TOOL>
</METAINFO>
"""

    # 3. schematic.xml
    # Defines the visual schematic layout, AT89C51 microcontroller, L298 driver, LCD1602 display,
    # MOTOR-ENCODER, buttons, pull-up resistors and exact netlist wire links.
    schematic_xml = """<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<SCHEMATIC AUTHOR="C51 PID Team" TITLE="AT89C51 Motor PID Closed-Loop Control System">
  <PROPERTIES>
    <PROPERTY NAME="GRID" VALUE="1"/>
    <PROPERTY NAME="SHOWGRID" VALUE="1"/>
  </PROPERTIES>
  
  <COMPONENTS>
    <!-- AT89C51 MCU -->
    <COMPONENT ID="U1" TYPE="AT89C51">
      <PROPERTIES>
        <PROPERTY NAME="REF" VALUE="U1"/>
        <PROPERTY NAME="VALUE" VALUE="AT89C51"/>
        <PROPERTY NAME="PRGFILE" VALUE="main.hex"/>
        <PROPERTY NAME="CLOCK" VALUE="12MHz"/>
      </PROPERTIES>
      <POSITION X="100" Y="100"/>
    </COMPONENT>

    <!-- L298N Motor Driver -->
    <COMPONENT ID="U2" TYPE="L298">
      <PROPERTIES>
        <PROPERTY NAME="REF" VALUE="U2"/>
        <PROPERTY NAME="VALUE" VALUE="L298"/>
      </PROPERTIES>
      <POSITION X="180" Y="100"/>
    </COMPONENT>

    <!-- MOTOR-ENCODER DC Motor -->
    <COMPONENT ID="M1" TYPE="MOTOR-ENCODER">
      <PROPERTIES>
        <PROPERTY NAME="REF" VALUE="M1"/>
        <PROPERTY NAME="VALUE" VALUE="MOTOR-ENCODER"/>
        <PROPERTY NAME="PULSES" VALUE="30"/>
        <PROPERTY NAME="VOLTAGE" VALUE="12V"/>
      </PROPERTIES>
      <POSITION X="240" Y="100"/>
    </COMPONENT>

    <!-- LCD1602 Display (LM016L) -->
    <COMPONENT ID="LCD1" TYPE="LM016L">
      <PROPERTIES>
        <PROPERTY NAME="REF" VALUE="LCD1"/>
        <PROPERTY NAME="VALUE" VALUE="LM016L"/>
      </PROPERTIES>
      <POSITION X="100" Y="40"/>
    </COMPONENT>

    <!-- Key UP Button -->
    <COMPONENT ID="SW1" TYPE="BUTTON">
      <PROPERTIES>
        <PROPERTY NAME="REF" VALUE="SW1"/>
        <PROPERTY NAME="VALUE" VALUE="KEY_UP"/>
      </PROPERTIES>
      <POSITION X="40" Y="120"/>
    </COMPONENT>

    <!-- Key DOWN Button -->
    <COMPONENT ID="SW2" TYPE="BUTTON">
      <PROPERTIES>
        <PROPERTY NAME="REF" VALUE="SW2"/>
        <PROPERTY NAME="VALUE" VALUE="KEY_DOWN"/>
      </PROPERTIES>
      <POSITION X="40" Y="140"/>
    </COMPONENT>

    <!-- Key STOP Button -->
    <COMPONENT ID="SW3" TYPE="BUTTON">
      <PROPERTIES>
        <PROPERTY NAME="REF" VALUE="SW3"/>
        <PROPERTY NAME="VALUE" VALUE="KEY_STOP"/>
      </PROPERTIES>
      <POSITION X="40" Y="160"/>
    </COMPONENT>
    
    <!-- RESPACK P0 Pull-up Resistor -->
    <COMPONENT ID="RP1" TYPE="RESPACK">
      <PROPERTIES>
        <PROPERTY NAME="REF" VALUE="RP1"/>
        <PROPERTY NAME="VALUE" VALUE="10k"/>
      </PROPERTIES>
      <POSITION X="80" Y="70"/>
    </COMPONENT>
  </COMPONENTS>

  <NETS>
    <!-- PWM Control Link -->
    <NET NAME="PWM">
      <CONNECTION COMPONENT="U1" PIN="P1.0"/>
      <CONNECTION COMPONENT="U2" PIN="ENA"/>
    </NET>

    <!-- Motor Input 1 -->
    <NET NAME="IN1">
      <CONNECTION COMPONENT="U1" PIN="P1.1"/>
      <CONNECTION COMPONENT="U2" PIN="IN1"/>
    </NET>

    <!-- Motor Input 2 -->
    <NET NAME="IN2">
      <CONNECTION COMPONENT="U1" PIN="P1.2"/>
      <CONNECTION COMPONENT="U2" PIN="IN2"/>
    </NET>

    <!-- Motor Output 1 to Driver -->
    <NET NAME="OUT1">
      <CONNECTION COMPONENT="U2" PIN="OUT1"/>
      <CONNECTION COMPONENT="M1" PIN="IN+"/>
    </NET>

    <!-- Motor Output 2 to Driver -->
    <NET NAME="OUT2">
      <CONNECTION COMPONENT="U2" PIN="OUT2"/>
      <CONNECTION COMPONENT="M1" PIN="IN-"/>
    </NET>

    <!-- Encoder Feedback to INT0 -->
    <NET NAME="ENCODER_OUT">
      <CONNECTION COMPONENT="M1" PIN="OUT_A"/>
      <CONNECTION COMPONENT="U1" PIN="P3.2"/>
    </NET>

    <!-- LCD Control RS -->
    <NET NAME="LCD_RS">
      <CONNECTION COMPONENT="U1" PIN="P2.0"/>
      <CONNECTION COMPONENT="LCD1" PIN="RS"/>
    </NET>

    <!-- LCD Control RW -->
    <NET NAME="LCD_RW">
      <CONNECTION COMPONENT="U1" PIN="P2.1"/>
      <CONNECTION COMPONENT="LCD1" PIN="RW"/>
    </NET>

    <!-- LCD Control E -->
    <NET NAME="LCD_E">
      <CONNECTION COMPONENT="U1" PIN="P2.2"/>
      <CONNECTION COMPONENT="LCD1" PIN="E"/>
    </NET>

    <!-- LCD Data Bus P0 to D0-D7 -->
    <NET NAME="D0">
      <CONNECTION COMPONENT="U1" PIN="P0.0"/>
      <CONNECTION COMPONENT="RP1" PIN="1"/>
      <CONNECTION COMPONENT="LCD1" PIN="D0"/>
    </NET>
    <NET NAME="D1">
      <CONNECTION COMPONENT="U1" PIN="P0.1"/>
      <CONNECTION COMPONENT="RP1" PIN="2"/>
      <CONNECTION COMPONENT="LCD1" PIN="D1"/>
    </NET>
    <NET NAME="D2">
      <CONNECTION COMPONENT="U1" PIN="P0.2"/>
      <CONNECTION COMPONENT="RP1" PIN="3"/>
      <CONNECTION COMPONENT="LCD1" PIN="D2"/>
    </NET>
    <NET NAME="D3">
      <CONNECTION COMPONENT="U1" PIN="P0.3"/>
      <CONNECTION COMPONENT="RP1" PIN="4"/>
      <CONNECTION COMPONENT="LCD1" PIN="D3"/>
    </NET>
    <NET NAME="D4">
      <CONNECTION COMPONENT="U1" PIN="P0.4"/>
      <CONNECTION COMPONENT="RP1" PIN="5"/>
      <CONNECTION COMPONENT="LCD1" PIN="D4"/>
    </NET>
    <NET NAME="D5">
      <CONNECTION COMPONENT="U1" PIN="P0.5"/>
      <CONNECTION COMPONENT="RP1" PIN="6"/>
      <CONNECTION COMPONENT="LCD1" PIN="D5"/>
    </NET>
    <NET NAME="D6">
      <CONNECTION COMPONENT="U1" PIN="P0.6"/>
      <CONNECTION COMPONENT="RP1" PIN="7"/>
      <CONNECTION COMPONENT="LCD1" PIN="D6"/>
    </NET>
    <NET NAME="D7">
      <CONNECTION COMPONENT="U1" PIN="P0.7"/>
      <CONNECTION COMPONENT="RP1" PIN="8"/>
      <CONNECTION COMPONENT="LCD1" PIN="D7"/>
    </NET>

    <!-- KEY UP -->
    <NET NAME="KEY_UP_NET">
      <CONNECTION COMPONENT="U1" PIN="P3.4"/>
      <CONNECTION COMPONENT="SW1" PIN="1"/>
    </NET>

    <!-- KEY DOWN -->
    <NET NAME="KEY_DOWN_NET">
      <CONNECTION COMPONENT="U1" PIN="P3.5"/>
      <CONNECTION COMPONENT="SW2" PIN="1"/>
    </NET>

    <!-- KEY STOP -->
    <NET NAME="KEY_STOP_NET">
      <CONNECTION COMPONENT="U1" PIN="P3.6"/>
      <CONNECTION COMPONENT="SW3" PIN="1"/>
    </NET>
  </NETS>
</SCHEMATIC>
"""

    # Pack files to zip with .pdsprj extension
    print(f"[Proteus Gen] Packaging project files into {output_path}...")
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.xml", project_xml)
        z.writestr("metainfo.xml", metainfo_xml)
        z.writestr("schematic.xml", schematic_xml)
        
    print("[Proteus Gen] Complete! Proteus 8 project file generated successfully.")

if __name__ == "__main__":
    create_pdsprj()
