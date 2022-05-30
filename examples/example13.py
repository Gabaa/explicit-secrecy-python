import expsec

# Safe: list is constructed from only public values
a = expsec.Public(10)
b = expsec.Public(12)
lst = [a, b]
print(lst)
