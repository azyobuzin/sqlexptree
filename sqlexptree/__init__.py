"""
SqlExpTree
A Building SQL Utility

Copyright (c) 2013 azyobuzin
license: The MIT License, see http://opensource.org/licenses/mit-license.php
"""

__author__ = "azyobuzin"
__version__ = "1.0"

import decimal

def _escape_string(s):
    assert isinstance(s, str)
    return (s.replace("\0", "\\0")
            .replace("'", "\\'")
            .replace("\"", "\\\"")
            .replace("\b", "\\b")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
            .replace("\032", "\\Z")
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_"))

def _quote_string(s):
    assert isinstance(s, str)
    return "'" + _escape_string(s) + "'"

def _quote(obj):
    if obj is None:
        return "NULL"
    if isinstance(obj, bool):
        return "1" if obj else "0"
    if isinstance(obj, SNameBase):
        return "*"
    if isinstance(obj, (int, float, decimal.Decimal, _SOperatable)):
        return str(obj)
    if isinstance(obj, str):
        return _quote_string(obj)
    raise TypeError()

def _quote_identifier(s):
    assert isinstance(s, str)
    return "`" + s.replace("`", "``") + "`"

class SqlBuilder(object):
    """A object to build SQL."""

    def __init__(self, sql=""):
        self._sql = sql

    def build(self):
        """Returns the built SQL string."""
        return self._sql.strip()

    def __str__(self):
        return self.build()

    def append(self, s):
        """Returns the SqlBuilder object appended specified raw SQL."""
        return SqlBuilder(self._sql + " " + s)

    def from_tables(self, tables):
        """
        FROM syntax
        
        tables: the table name or a list of the table names
        """

        if not isinstance(tables, (list, tuple)):
            tables = [tables]
        return self.append("from " + ", ".join(_quote_identifier(table) for table in tables))

    FROM = from_tables

    def select(self, selector):
        """
        SELECT syntax

        selector: the function that returns expression list or dict
                  example * lambda _: _ #equals "*"
                          * lambda _: _.column
                          * lambda _: _.now()
                          * lambda _: [_.column0, _.column1]
                          * lambda _: { "A": _.column0, "": _.column1 }
        """
        
        if isinstance(selector, str):
            return self.append("select " + selector)

        result = selector(SNameBase())
        if isinstance(result, dict):
            select_expr = ", ".join(_quote_identifier(key) + " as " + _quote(value) for key, value in result.items())
        elif isinstance(result, (list, tuple)):
            select_expr = ",".join(_quote(obj) for obj in result)
        else:
            select_expr = _quote(result)
        return self.append("select " + select_expr)

    SELECT = select

    def where(self, predicate):
        """
        WHERE clause

        predicate: the function that returns expression
                   example * lambda _: op_and(_.column0 > 5, _.column1 < 10)
        """

        if isinstance(predicate, str):
            return self.append("where " + predicate)

        return self.append("where " + _quote(predicate(SNameBase())))

class SNameBase(object):
    def __getattr__(self, name):
        return SName([name])

class _SOperatable(object):
    def __lt__(self, other):
        return SOperator("<", self, other)

    def __le__(self, other):
        return SOperator("<=", self, other)

    def __eq__(self, other):
        return SOperator("is", self, other) if other is None else SOperator("=", self, other)

    def __ne__(self, other):
        return SOperator("is not", self, other) if other is None else SOperator("<>", self, other)

    def __gt__(self, other):
        return SOperator(">", self, other)
    
    def __ge__(self, other):
        return SOperator(">=", self, other)

    def __add__(self, other):
        return SOperator("+", self, other)

    def __radd__(self, other):
        return SOperator("+", other, self)

    def __sub__(self, other):
        return SOperator("-", self, other)

    def __rsub__(self, other):
        return SOperator("-", other, self)

    def __mul__(self, other):
        return SOperator("*", self, other)

    def __rmul__(self, other):
        return SOperator("*", other, self)

    def __div__(self, other):
        return SOperator("/", self, other)

    def __rdiv__(self, other):
        return SOperator("/", other, self)

    def __truediv__(self, other):
        return SOperator("/", self, other)

    def __rtruediv__(self, other):
        return SOperator("/", other, self)

    def __floordiv__(self, other):
        return SOperator("div", self, other)

    def __rfloordiv__(self, other):
        return SOperator("div", other, self)

    def __mod__(self, other):
        return SMethod(["mod"], (self, other))

    def __rmod__(self, other):
        return SMethod(["mod"], (other, self))

    def __pow__(self, other):
        return SMethod(["pow"], (self, other))

    def __rpow__(self, other):
        return SMethod(["pow"], (other, self))

    def __lshift__(self, other):
        return SOperator("<<", self, other)

    def __rlshift__(self, other):
        return SOperator("<<", other, self)

    def __rshift__(self, other):
        return SOperator(">>", self, other)

    def __rrshift__(self, other):
        return SOperator(">>", other, self)

    def __and__(self, other):
        return SOperator("&", self, other)

    def __rand__(self, other):
        return SOperator("&", other, self)

    def __xor__(self, other):
        return SOperator("^", self, other)

    def __rxor__(self, other):
        return SOperator("^", other, self)

    def __or__(self, other):
        return SOperator("|", self, other)

    def __ror__(self, other):
        return SOperator("|", other, self)

    def __neg__(self):
        return SSingleOperator("-", self)

    def __pos__(self):
        return SSingleOperator("+", self)

    def __abs__(self):
        return SMethod(["abs"], (self,))

class SName(_SOperatable):
    def __init__(self, name_list):
        self.__name_list = list(name_list)

    def __str__(self):
        return ".".join(_quote_identifier(s) for s in self.__name_list)

    def __getattr__(self, name):
        return SName(self.__name_list + [name])

    def __call__(self, *args):
        return SMethod(self.__name_list, args)

class SMethod(_SOperatable):
    def __init__(self, name_list, args):
        self.__name_list = list(name_list)
        self.__args = args

    def __str__(self):
        return (".".join([_quote_identifier(s) for s in self.__name_list[0:-1]] + [self.__name_list[-1]])
                + "(" + ", ".join(_quote(arg) for arg in self.__args) + ")")

class SOperator(_SOperatable):
    def __init__(self, op_name, left, right):
        assert isinstance(op_name, str)
        self.op_name = op_name
        self.left = left
        self.right = right

    def __str__(self):
        return "(" + _quote(self.left) + " " + self.op_name + " " + _quote(self.right) + ")"

class SSingleOperator(_SOperatable):
    def __init__(self, op_name, expr):
        assert isinstance(op_name, str)
        self.op_name = op_name
        self.expr = expr

    def __str__(self):
        return "(" + self.op_name + " " + _quote(self.expr) + ")"

def op_or(*exprs):
    op = SOperator("or", exprs[0], exprs[1])
    for expr in exprs[2:]:
        op = SOperator("or", op, expr)
    return op

def op_xor(left, right):
    return SOperator("xor", left, right)

def op_and(*exprs):
    op = SOperator("and", exprs[0], exprs[1])
    for expr in exprs[2:]:
        op = SOperator("and", op, expr)
    return op

def op_not(expr):
    return SSingleOperator("not", expr)
