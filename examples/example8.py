"""
Safe: `a` is either declassified or assigned public value

expsec_public: b, c
"""

a = 10
b = 20
c = 30
if a < 0:
    a = b
else:
    a = c
print(a)
