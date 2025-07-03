#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    int id;
    char name[50];
} Student;

int add_numbers(int a, int b) {
    return a + b;
}

int multiply_numbers(int x, int y) {
    int result = x * y;
    return result;
}

void print_student(Student* student) {
    if (student != NULL) {
        printf("ID: %d, Name: %s\n", student->id, student->name);
    }
}

Student* create_student(int id, const char* name) {
    Student* student = malloc(sizeof(Student));
    if (student != NULL) {
        student->id = id;
        strcpy(student->name, name);
    }
    return student;
}

int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return multiply_numbers(n, factorial(n - 1));
}

int main() {
    printf("Single File Analysis Example\n");
    
    int sum = add_numbers(10, 20);
    int product = multiply_numbers(5, 6);
    printf("Sum: %d, Product: %d\n", sum, product);
    
    int fact = factorial(5);
    printf("Factorial: %d\n", fact);
    
    Student* student = create_student(1001, "Alice");
    if (student) {
        print_student(student);
        free(student);
    }
    
    return 0;
}