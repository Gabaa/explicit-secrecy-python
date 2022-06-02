"""
Safe: b is public and flows to a

expsec_public: b
"""

a = 4
b = [1, 2, 3]
a = b[0]
print(a)
