import expsec

# Unsafe
a = 10
b = expsec.Public(a)
print(a)
