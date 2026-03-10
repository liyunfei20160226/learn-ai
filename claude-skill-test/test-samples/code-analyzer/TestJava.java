/**
 * 测试Java文件 - 用于代码分析测试
 * 这是一个多行注释示例
 */

// 单行注释
public class TestJava {

    // 常量
    private static final String GREETING = "Hello";

    // 成员变量
    private int counter;

    /**
     * 构造函数
     */
    public TestJava() {
        this.counter = 0;
    }

    /**
     * 问候方法
     * @param name 姓名
     */
    public void greet(String name) {
        System.out.println(GREETING + ", " + name + "!");
    }

    // 计算两个数的和
    public int add(int a, int b) {
        // 返回和
        return a + b;
    }

    // 静态方法
    public static void staticMethod() {
        System.out.println("这是一个静态方法");
    }

    // 内部类
    private class InnerClass {
        public void innerMethod() {
            System.out.println("内部类方法");
        }
    }

    /**
     * 主方法
     * @param args 命令行参数
     */
    public static void main(String[] args) {
        // 创建实例
        TestJava test = new TestJava();

        // 调用方法
        test.greet("World");

        int sum = test.add(5, 3);
        System.out.println("5 + 3 = " + sum);

        // 调用静态方法
        staticMethod();

        // 创建内部类实例
        InnerClass inner = test.new InnerClass();
        inner.innerMethod();
    }
}