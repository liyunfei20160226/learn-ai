// 测试Go文件 - 用于代码分析测试
package main

import "fmt"

// 常量定义
const Version = "1.0.0"

// 全局变量
var counter = 0

// Greet 函数打印问候语
func Greet(name string) {
	fmt.Printf("Hello, %s!\n", name)
}

// Add 函数计算两个整数的和
func Add(a, b int) int {
	// 返回两个数的和
	return a + b
}

// Calculator 结构体
type Calculator struct {
	value int
}

// NewCalculator 创建新的计算器实例
func NewCalculator() *Calculator {
	return &Calculator{value: 0}
}

// Add 方法为计算器添加值
func (c *Calculator) Add(x int) int {
	c.value += x
	return c.value
}

// Reset 方法重置计算器
func (c *Calculator) Reset() {
	c.value = 0
}

// 接口定义
type MathOperation interface {
	Execute(a, b int) int
}

// 实现接口
type Addition struct{}

func (op Addition) Execute(a, b int) int {
	return a + b
}

// main 函数
func main() {
	// 调用函数
	Greet("World")

	// 计算和
	sum := Add(10, 20)
	fmt.Printf("10 + 20 = %d\n", sum)

	// 使用结构体
	calc := NewCalculator()
	calc.Add(5)
	calc.Add(10)
	fmt.Printf("计算器值: %d\n", calc.value)

	// 使用接口
	var op MathOperation = Addition{}
	result := op.Execute(7, 3)
	fmt.Printf("7 + 3 = %d\n", result)
}