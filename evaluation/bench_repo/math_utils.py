def add(a, b):
    return a + b


def factorial(n):
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0:
        return 1
    res = 1
    for i in range(1, n + 1):
        res *= i
    return res


def is_prime(n):
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def fibonacci(n):
    if n < 0:
        raise ValueError("Fibonacci not defined for negative numbers")
    if n == 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def clamp(val, min_val, max_val):
    if min_val > max_val:
        raise ValueError("min_val cannot exceed max_val")
    return max(min_val, min(val, max_val))


def power(base, exp):
    return base ** exp

