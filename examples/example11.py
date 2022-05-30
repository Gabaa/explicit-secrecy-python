import expsec

# Safe: This declassifies both `a` and `b`
a = [1, 2, 3]
b = expsec.Public(a)
print(a)
