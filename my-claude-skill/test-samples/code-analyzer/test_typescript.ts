/**
 * 测试TypeScript文件 - 用于代码分析测试
 * 这是一个多行注释示例
 */

// 单行注释
const MAX_RETRIES: number = 3;

// 接口定义
interface Person {
    name: string;
    age: number;
}

// 类型别名
type Operation = (a: number, b: number) => number;

// 函数定义
function greet(person: Person): string {
    return `Hello, ${person.name}!`;
}

// 箭头函数
const add: Operation = (a: number, b: number): number => {
    // 计算两个数的和
    return a + b;
};

// 类定义
class Calculator {
    private value: number;

    constructor(initialValue: number = 0) {
        this.value = initialValue;
    }

    /**
     * 添加值到计算器
     * @param x 要添加的值
     * @returns 新的值
     */
    public add(x: number): number {
        this.value += x;
        return this.value;
    }

    // 重置计算器
    public reset(): void {
        this.value = 0;
    }

    // 获取当前值
    public getValue(): number {
        return this.value;
    }
}

// 泛型函数
function identity<T>(value: T): T {
    return value;
}

// 枚举
enum Color {
    Red = "RED",
    Green = "GREEN",
    Blue = "BLUE"
}

// 主函数
const main = (): void => {
    // 创建对象
    const person: Person = { name: "World", age: 30 };

    // 调用函数
    const message = greet(person);
    console.log(message);

    // 计算
    const sum = add(10, 20);
    console.log(`10 + 20 = ${sum}`);

    // 使用类
    const calc = new Calculator();
    calc.add(5);
    calc.add(10);
    console.log(`计算器值: ${calc.getValue()}`);

    // 使用泛型
    const result = identity<string>("TypeScript");
    console.log(`泛型结果: ${result}`);

    // 使用枚举
    console.log(`颜色: ${Color.Red}`);
};

// 调用主函数
main();