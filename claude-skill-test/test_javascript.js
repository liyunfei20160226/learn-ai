/**
 * 测试JavaScript文件 - 用于代码分析测试
 * 这是一个多行注释示例
 */

// 单行注释
const PI = 3.14159;

// 函数定义
function greet(name) {
    console.log(`Hello, ${name}!`);
    return true;
}

// 箭头函数
const add = (a, b) => {
    // 计算两个数的和
    const result = a + b;
    return result;
};

// 类定义
class Calculator {
    constructor() {
        this.value = 0;
    }

    /**
     * 添加值到计算器
     * @param {number} x - 要添加的值
     * @returns {number} - 新的值
     */
    add(x) {
        this.value += x;
        return this.value;
    }

    // 重置计算器
    reset() {
        this.value = 0;
    }
}

// 对象字面量中的方法
const utils = {
    // 工具函数
    multiply: function(a, b) {
        return a * b;
    },

    // 简写方法
    divide(a, b) {
        if (b === 0) {
            throw new Error("除数不能为零");
        }
        return a / b;
    }
};

// 立即执行函数
(function() {
    console.log("立即执行函数");
})();

// 主执行
const main = () => {
    greet("World");

    const sum = add(5, 3);
    console.log(`5 + 3 = ${sum}`);

    const calc = new Calculator();
    calc.add(10);
    calc.add(5);
    console.log(`计算器值: ${calc.value}`);

    const product = utils.multiply(4, 6);
    console.log(`4 * 6 = ${product}`);
};

// 调用主函数
main();