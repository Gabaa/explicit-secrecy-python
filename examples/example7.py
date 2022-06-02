"""
Unsafe: `a` may be secret

expsec_public: b
"""

a = 10
b = 20
if a < 0:
    a = b
else:
    pass
print(a)
