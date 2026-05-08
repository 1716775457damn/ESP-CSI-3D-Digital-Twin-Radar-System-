/**
 * =========================================================================
 * 🎓 C51 单片机直流电机 PID 闭环控制系统固件 (全新极简兼容版)
 * =========================================================================
 * 适用单片机: AT89C51 / AT89S52 (采用 12.0MHz 晶振)
 * 硬件资源: 
 *   - P1.0 -> PWM 控制输出 (驱动 NPN 三极管或 L298N 的 EN 使能端)
 *   - P1.1 -> IN1 方向控制 (固定输出高电平 1)
 *   - P1.2 -> IN2 方向控制 (固定输出低电平 0)
 *   - P3.2 (INT0) -> 接收直流电机测速码盘反馈脉冲 (外部中断0)
 *   - P2.0 (RS), P2.1 (RW), P2.2 (EN) -> LCD1602 控制端
 *   - P0.0 - P0.7 -> LCD1602 数据总线 (需外接 10k 排阻上拉)
 *   - P3.4 (KEY_UP) -> 目标速度增加按键
 *   - P3.5 (KEY_DOWN) -> 目标速度减少按键
 *   - P3.6 (KEY_ON_OFF) -> 系统启停控制按键
 * =========================================================================
 */

#include <reg51.h>

/* 引脚重命名定义 */
sbit RS = P2^0;
sbit RW = P2^1;
sbit EN = P2^2;

sbit PWM_PIN   = P1^0;  /* 软件 PWM 输出脚 */
sbit DIR_IN1   = P1^1;  /* 电机方向正极 */
sbit DIR_IN2   = P1^2;  /* 电机方向负极 */

sbit KEY_UP     = P3^4;  /* 加速键 */
sbit KEY_DOWN   = P3^5;  /* 减速键 */
sbit KEY_STOP   = P3^6;  /* 启停键 */

/* 系统控制变量 */
volatile unsigned int pulse_count = 0; /* 存储中断捕获到的脉冲计数值 */
unsigned int current_speed = 0;        /* 当前计算出的转速 (RPM) */
unsigned int target_speed = 100;       /* 设定目标期望转速 (RPM) */
bit system_active = 1;                 /* 系统运行标志位 (1:运行, 0:急停) */

unsigned char pwm_duty = 40;           /* PWM 占空比变量 (0 - 100) */
unsigned char pwm_timer_step = 0;      /* Timer0 产生的 PWM 时间分度计 */

/* 经典 PID 控制算法变量 */
int err = 0;                           /* 当前误差: e(k) = target - current */
int err_last = 0;                      /* 上一次的误差: e(k-1) */
int err_integral = 0;                  /* 积分误差累加和: ∑e */

/* 调试好的高稳定度 PID 增益常数 */
float Kp = 1.35;                       /* 比例系数: 快速响应误差 */
float Ki = 0.22;                       /* 积分系数: 消除静差，提高精度 */
float Kd = 0.08;                       /* 微分系数: 预测误差走势，减小过冲 */

/* 毫秒级延时子程序 (12MHz晶振专用) */
void delay_ms(unsigned int ms) {
    unsigned int i, j;
    for (i = 0; i < ms; i++) {
        for (j = 0; j < 120; j++);
    }
}

/* =========================================================================
 * LCD1602 液晶屏驱动底层函数组
 * =========================================================================
 */

/* 向液晶屏写入指令 */
void Write_Cmd(unsigned char cmd) {
    RS = 0; /* 选择指令寄存器 */
    RW = 0; /* 选择写入模式 */
    P0 = cmd;
    EN = 1; /* 产生高脉冲 */
    delay_ms(1);
    EN = 0; /* 拉低使数据锁存 */
    delay_ms(2);
}

/* 向液晶屏写入数据 */
void Write_Data(unsigned char dat) {
    RS = 1; /* 选择数据寄存器 */
    RW = 0; /* 选择写入模式 */
    P0 = dat;
    EN = 1; /* 产生高脉冲 */
    delay_ms(1);
    EN = 0; /* 拉低使数据锁存 */
    delay_ms(2);
}

/* 液晶屏初始化 */
void LCD_Init() {
    Write_Cmd(0x38); /* 8位数据总线，双行显示，5x7点阵 */
    Write_Cmd(0x0C); /* 开显示，无光标 */
    Write_Cmd(0x06); /* 写入数据后光标右移 */
    Write_Cmd(0x01); /* 清除屏幕显示 */
    delay_ms(5);
}

/* 在指定位置显示字符串 */
void Show_String(unsigned char row, unsigned char col, char *str) {
    unsigned char addr;
    if (row == 1) {
        addr = 0x80 + col - 1; /* 第一行起始地址 */
    } else {
        addr = 0xC0 + col - 1; /* 第二行起始地址 */
    }
    Write_Cmd(addr);
    while (*str) {
        Write_Data(*str++);
    }
}

/* 在指定位置显示一个固定长度的整数 */
void Show_Number(unsigned char row, unsigned char col, unsigned int num, unsigned char len) {
    char temp[6];
    unsigned char i;
    for (i = 0; i < len; i++) {
        temp[len - 1 - i] = '0' + (num % 10);
        num /= 10;
    }
    temp[len] = '\0';
    Show_String(row, col, temp);
}

/* =========================================================================
 * 中断服务程序 (Interrupt Service Routines)
 * =========================================================================
 */

/* 外部中断0: 用于读取测速编码器的脉冲 */
void External_Int0_ISR(void) interrupt 0 {
    pulse_count++; /* 每一个脉冲下降沿到来，计数值自增 1 */
}

/* 定时器0中断: 每 1ms 触发一次，用于软件产生 100Hz 的高频 PWM */
void Timer0_ISR(void) interrupt 1 {
    /* 重装 1ms 初值 */
    TH0 = 0xFC;
    TL0 = 0x18;
    
    pwm_timer_step++;
    if (pwm_timer_step >= 100) {
        pwm_timer_step = 0; /* PWM周期划分为 100 等份 */
    }
    
    if (system_active) {
        if (pwm_timer_step < pwm_duty) {
            PWM_PIN = 1; /* 占空比高电平时间 */
        } else {
            PWM_PIN = 0; /* 占空比低电平时间 */
        }
    } else {
        PWM_PIN = 0;     /* 系统关闭时保持低电平 */
    }
}

/* 定时器1中断: 每 50ms 触发一次，作为控制环路的精准主时钟 */
void Timer1_ISR(void) interrupt 3 {
    static unsigned char time_count = 0;
    float temp_output = 0.0;
    
    /* 重装 50ms 初值 */
    TH1 = 0x3C;
    TL1 = 0xB0;
    
    time_count++;
    if (time_count >= 4) { /* 累计达 200ms (采样频率为 5Hz) */
        time_count = 0;
        
        /* 
         * 速度公式计算 (RPM):
         * 假设直流电机的测速码盘为 30 线 (每转产生 30 个脉冲)。
         * 200毫秒 (0.2秒) 内累计的脉冲数为 pulse_count。
         * 转速 = (pulse_count / 30) * (60秒 / 0.2秒) = pulse_count * 10
         */
        current_speed = pulse_count * 10;
        pulse_count = 0; /* 计数器清空，开始下一次 200ms 的计数 */
        
        if (system_active) {
            /* 1. 计算当前偏差值 */
            err = target_speed - current_speed;
            
            /* 2. 积分误差累积，并加入抗饱和限幅 (Anti-Windup) 防止过冲超调 */
            err_integral += err;
            if (err_integral > 150)  err_integral = 150;
            if (err_integral < -150) err_integral = -150;
            
            /* 3. 经典位置式 PID 计算公式 */
            temp_output = Kp * err + Ki * err_integral + Kd * (err - err_last);
            
            /* 4. 将 PID 控制输出值限制在 PWM 有效占空比 [0, 100]% 范围内 */
            if (temp_output > 100.0) temp_output = 100.0;
            if (temp_output < 0.0)   temp_output = 0.0;
            
            pwm_duty = (unsigned char)temp_output; /* 更新 PWM 占空比 */
            err_last = err; /* 缓存本次误差，供给下一次微分 D 计算 */
        } else {
            pwm_duty = 0;
            err_integral = 0;
            err_last = 0;
        }
    }
}

/* =========================================================================
 * 独立按键扫描及软件消抖子程序
 * =========================================================================
 */
void Scan_Keys() {
    /* 加速按键扫描 */
    if (KEY_UP == 0) {
        delay_ms(10); /* 软件延时消抖 */
        if (KEY_UP == 0) {
            target_speed += 10;
            if (target_speed > 250) target_speed = 250; /* 限制最高速度 */
            while (KEY_UP == 0); /* 等待按键松开，防止连续触发 */
        }
    }
    
    /* 减速按键扫描 */
    if (KEY_DOWN == 0) {
        delay_ms(10); /* 软件延时消抖 */
        if (KEY_DOWN == 0) {
            if (target_speed >= 10) {
                target_speed -= 10;
            } else {
                target_speed = 0;
            }
            while (KEY_DOWN == 0); /* 等待松开 */
        }
    }
    
    /* 启停按键扫描 */
    if (KEY_STOP == 0) {
        delay_ms(10); /* 软件延时消抖 */
        if (KEY_STOP == 0) {
            system_active = !system_active;
            if (!system_active) {
                pwm_duty = 0; /* 急停时瞬间关闭 PWM 输出 */
            }
            while (KEY_STOP == 0); /* 等待松开 */
        }
    }
}

/* =========================================================================
 * 主函数入口 (Main Program Loop)
 * =========================================================================
 */
void main() {
    /* 初始化驱动端: 预设正转，PWM 输出引脚初始拉低 */
    DIR_IN1 = 1;
    DIR_IN2 = 0;
    PWM_PIN = 0;
    
    /* 初始化 LCD1602 并写入静止模版字符 */
    LCD_Init();
    Show_String(1, 1, "Set Speed:000RPM");
    Show_String(2, 1, "Cur Speed:000RPM");
    
    /* 
     * 定时器模式配置:
     * TMOD = 0x11 表示定时器0、定时器1 均工作在 16位定时器模式 (Mode 1)
     */
    TMOD = 0x11;
    
    /* 初始化定时器0 (1ms 溢出值) */
    TH0 = 0xFC;
    TL0 = 0x18;
    
    /* 初始化定时器1 (50ms 溢出值) */
    TH1 = 0x3C;
    TL1 = 0xB0;
    
    /* 设置外部中断0 (INT0) 触发模式为下降沿触发 (1) */
    IT0 = 1;
    
    /* 开启中断使能控制位 */
    EX0 = 1;  /* 开启外部中断0 */
    ET0 = 1;  /* 开启定时器0中断 */
    ET1 = 1;  /* 开启定时器1中断 */
    EA  = 1;  /* 开启全局中断允许位 */
    
    /* 启动定时器运行 */
    TR0 = 1;  /* 启动定时器0 */
    TR1 = 1;  /* 启动定时器1 */
    
    /* 主循环，负责扫描按键并按设定的时间间隔更新液晶屏幕数值 */
    while (1) {
        Scan_Keys();
        
        /* 刷新 LCD 屏幕上的目标速度和实际测量速度 */
        Show_Number(1, 11, target_speed, 3);
        Show_Number(2, 11, current_speed, 3);
        
        delay_ms(10);
    }
}
