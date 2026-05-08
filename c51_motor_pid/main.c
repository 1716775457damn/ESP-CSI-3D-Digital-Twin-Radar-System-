/**
 * =========================================================================
 * 51 MCU PID Motor Speed Control System Firmware
 * =========================================================================
 * MCU: AT89C51 / AT89S52 (12MHz Quartz Crystal)
 * Peripherals: LCD1602, L298N Motor Driver, DC Encoder Motor, Keys
 * 
 * Compiler: Keil C51 / SDCC
 * =========================================================================
 */

#include <reg51.h>

/* LCD1602 Pin Declarations */
sbit LCD_RS = P2^0;
sbit LCD_RW = P2^1;
sbit LCD_EN = P2^2;

/* L298N Motor Driver Pin Declarations */
sbit MOTOR_PWM = P1^0;  /* Connect to ENA on L298N */
sbit MOTOR_IN1 = P1^1;  /* Connect to IN1 on L298N */
sbit MOTOR_IN2 = P1^2;  /* Connect to IN2 on L298N */

/* Function Key Pin Declarations */
sbit KEY_UP   = P3^4;   /* Speed increment (+10 RPM) */
sbit KEY_DOWN = P3^5;   /* Speed decrement (-10 RPM) */
sbit KEY_STOP = P3^6;   /* Toggle Motor ON/OFF */

/* Global Variable Definitions */
volatile unsigned int pulse_count = 0;  /* Encoder ticks counted via INT0 */
unsigned int current_speed = 0;         /* Current speed (RPM) */
unsigned int target_speed = 120;        /* Target speed setting (RPM), Default 120 */
bit motor_running = 1;                  /* 1 = PID Active, 0 = Emergency Stop */

unsigned char pwm_duty = 30;            /* Modulated PWM duty cycle (0-100) */
unsigned char pwm_tick = 0;             /* Timer 0 interrupt PWM step counter */

/* Positional PID Controller States */
int error = 0;
int error_last = 0;
int error_sum = 0;

/* High-Stability Tuned PID Gains */
float Kp = 1.45;
float Ki = 0.28;
float Kd = 0.12;

/* Delay function for LCD & debouncing (accurate at 12MHz) */
void delay_ms(unsigned int ms) {
    unsigned int i, j;
    for (i = 0; i < ms; i++) {
        for (j = 0; j < 120; j++);
    }
}

/* =========================================================================
 * LCD1602 Character Screen Driver
 * =========================================================================
 */
void LCD_WriteCmd(unsigned char cmd) {
    LCD_RS = 0;
    LCD_RW = 0;
    P0 = cmd;
    LCD_EN = 1;
    delay_ms(1);
    LCD_EN = 0;
    delay_ms(2);
}

void LCD_WriteData(unsigned char dat) {
    LCD_RS = 1;
    LCD_RW = 0;
    P0 = dat;
    LCD_EN = 1;
    delay_ms(1);
    LCD_EN = 0;
    delay_ms(2);
}

void LCD_Init() {
    LCD_WriteCmd(0x38);  /* 16x2 lines, 5x7 Font */
    LCD_WriteCmd(0x0C);  /* Display ON, Cursor OFF, No Blink */
    LCD_WriteCmd(0x06);  /* Increment cursor */
    LCD_WriteCmd(0x01);  /* Clear Screen */
    delay_ms(5);
}

void LCD_ShowString(unsigned char row, unsigned char col, char *str) {
    unsigned char addr;
    if (row == 1) {
        addr = 0x80 + col - 1;
    } else {
        addr = 0xC0 + col - 1;
    }
    LCD_WriteCmd(addr);
    while (*str) {
        LCD_WriteData(*str++);
    }
}

void LCD_ShowNum(unsigned char row, unsigned char col, unsigned int num, unsigned char length) {
    char buf[6];
    unsigned char i;
    for (i = 0; i < length; i++) {
        buf[length - 1 - i] = '0' + (num % 10);
        num /= 10;
    }
    buf[length] = '\0';
    LCD_ShowString(row, col, buf);
}

/* =========================================================================
 * External Interrupt 0 (INT0) Service Routine
 * =========================================================================
 * Handles incoming falling/rising edges from the motor's encoder disk.
 */
void INT0_ISR(void) interrupt 0 {
    pulse_count++;
}

/* =========================================================================
 * Timer 0 Interrupt Service Routine (1ms interrupts)
 * =========================================================================
 * Drives the software PWM cycle (Period = 100ms) on P1.0.
 */
void Timer0_ISR(void) interrupt 1 {
    /* Reload Timer 0 (1ms at 12MHz crystal oscillator) */
    TH0 = 0xFC;
    TL0 = 0x18;
    
    pwm_tick++;
    if (pwm_tick >= 100) {
        pwm_tick = 0;
    }
    
    if (motor_running) {
        if (pwm_tick < pwm_duty) {
            MOTOR_PWM = 1;
        } else {
            MOTOR_PWM = 0;
        }
    } else {
        MOTOR_PWM = 0;
    }
}

/* =========================================================================
 * Timer 1 Interrupt Service Routine (50ms interrupts)
 * =========================================================================
 * Serves as the sampling clock. Every 200ms (4 interrupts), we compute the
 * speed, calculate the closed-loop PID control signal, and update the LCD.
 */
void Timer1_ISR(void) interrupt 3 {
    static unsigned char sample_tick = 0;
    float pid_out = 0.0;
    
    /* Reload Timer 1 (50ms at 12MHz crystal) */
    TH1 = 0x3C;
    TL1 = 0xB0;
    
    sample_tick++;
    if (sample_tick >= 4) {  /* Execution every 200ms (5Hz sampling frequency) */
        sample_tick = 0;
        
        /* 
         * Speed Calculation (RPM):
         * Let N = 30 pulses per motor revolution.
         * sample_period = 0.20s.
         * RPM = (pulse_count / N) * (60s / 0.2s) = pulse_count * 300 / 30 = pulse_count * 10
         */
        current_speed = pulse_count * 10;
        pulse_count = 0;  /* Clear pulse buffer for next window */
        
        if (motor_running) {
            /* 1. Calculate Error */
            error = target_speed - current_speed;
            
            /* 2. Integral accumulation with Anti-Windup Clamping */
            error_sum += error;
            if (error_sum > 180)  error_sum = 180;
            if (error_sum < -180) error_sum = -180;
            
            /* 3. Positional PID control formula */
            pid_out = Kp * error + Ki * error_sum + Kd * (error - error_last);
            
            /* 4. Clamp output to valid PWM duty cycle [0, 100]% */
            if (pid_out > 100.0) pid_out = 100.0;
            if (pid_out < 0.0)   pid_out = 0.0;
            
            pwm_duty = (unsigned char)pid_out;
            error_last = error;
        } else {
            pwm_duty = 0;
            error_sum = 0;
            error_last = 0;
        }
    }
}

/* =========================================================================
 * User Key Interface Scan (Debounced)
 * =========================================================================
 */
void Key_Scan() {
    if (KEY_UP == 0) {
        delay_ms(8);
        if (KEY_UP == 0) {
            target_speed += 10;
            if (target_speed > 250) target_speed = 250;  /* Max speed limit */
            while (KEY_UP == 0);  /* Wait for button release */
        }
    }
    
    if (KEY_DOWN == 0) {
        delay_ms(8);
        if (KEY_DOWN == 0) {
            if (target_speed >= 10) {
                target_speed -= 10;
            } else {
                target_speed = 0;
            }
            while (KEY_DOWN == 0);
        }
    }
    
    if (KEY_STOP == 0) {
        delay_ms(8);
        if (KEY_STOP == 0) {
            motor_running = !motor_running;
            if (!motor_running) {
                pwm_duty = 0;
            }
            while (KEY_STOP == 0);
        }
    }
}

/* =========================================================================
 * Main Execution Entry Point
 * =========================================================================
 */
void main() {
    /* Initialize IN1 & IN2 for clockwise directional motor rotation */
    MOTOR_IN1 = 1;
    MOTOR_IN2 = 0;
    MOTOR_PWM = 0;
    
    /* System Initialization */
    LCD_Init();
    LCD_ShowString(1, 1, "Set Speed:000RPM");
    LCD_ShowString(2, 1, "Cur Speed:000RPM");
    
    /* 
     * Configure Timers & Interrupts:
     * TMOD = 0x11 (Timer 0 in 16-bit Timer Mode, Timer 1 in 16-bit Timer Mode)
     */
    TMOD = 0x11;
    
    /* Timer 0 initialization (1ms reload) */
    TH0 = 0xFC;
    TL0 = 0x18;
    
    /* Timer 1 initialization (50ms reload) */
    TH1 = 0x3C;
    TL1 = 0xB0;
    
    /* External Interrupt 0 (INT0) trigger configuration: 1 = falling edge */
    IT0 = 1;
    
    /* Enable Interrupts */
    EX0 = 1;  /* Enable INT0 */
    ET0 = 1;  /* Enable Timer 0 Interrupt */
    ET1 = 1;  /* Enable Timer 1 Interrupt */
    EA  = 1;  /* Enable Global Interrupts */
    
    /* Start Timers */
    TR0 = 1;  /* Start Timer 0 */
    TR1 = 1;  /* Start Timer 1 */
    
    /* Infinite Main Loop */
    while (1) {
        Key_Scan();
        
        /* Periodically refresh variable segments on LCD1602 */
        LCD_ShowNum(1, 11, target_speed, 3);
        LCD_ShowNum(2, 11, current_speed, 3);
        
        delay_ms(10);
    }
}
