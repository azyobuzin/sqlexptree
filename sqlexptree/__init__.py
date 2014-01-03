"""
SqlExpTree
A Building SQL Utility

Copyright (c) 2013 azyobuzin
license: The MIT License, see http://opensource.org/licenses/mit-license.php
"""

__author__ = "azyobuzin"
__version__ = "1.0"

if isinstance(u"", str):
    unicode = str

class SqlBuilder(object):
    """A object to build SQL."""

    def __init__(self, encoding="utf-8", sql=b""):
        self._encoding = encoding
        self._sql = sql

    def _as_bytes(self, s):
        if isinstance(s, bytes):
            return s
        if isinstance(s, (str, unicode)):
            return s.encode(self._encoding)
        raise TypeError()

    def _quote_string(self, s):
        return (b"'" + self._as_bytes(s)
                .replace(b"\0", b"\\0")
                .replace(b"'", b"\\'")
                .replace(b"\"", b"\\\"")
                .replace(b"\b", b"\\b")
                .replace(b"\n", b"\\n")
                .replace(b"\r", b"\\r")
                .replace(b"\t", b"\\t")
                .replace(b"\032", b"\\Z")
                .replace(b"\\", b"\\\\")
                .replace(b"%", b"\\%")
                .replace(b"_", b"\\_") + b"'")

    def _quote(self, obj):
        import datetime
        import decimal

        if obj is None:
            return b"NULL"
        if isinstance(obj, bool):
            return b"1" if obj else b"0"
        if isinstance(obj, SNameBase):
            return b"*"
        if isinstance(obj, (int, float, decimal.Decimal)):
            return self._as_bytes(str(obj))
        if isinstance(obj, datetime.datetime):
            return self._quote_string(obj.strftime("%Y-%m-%d %H:%M:%S"))
        if isinstance(obj, (datetime.date, datetime.time)):
            return self._quote_string(str(obj))
        if isinstance(obj, datetime.timedelta):
            return b"interval " + self._quote_string(str(obj.total_seconds())) + b" second_microsecond"
        if isinstance(obj, _SOperatable):
            return obj._to_bytes(self)
        if isinstance(obj, (str, unicode, bytes)):
            return self._quote_string(obj)
        raise TypeError()

    def _quote_identifier(self, s):
        return b"`" + self._as_bytes(s).replace(b"`", b"``") + b"`"

    def build(self):
        """Returns the built SQL bytes."""
        return self._sql.strip()

    def __bytes__(self):
        return self.build()

    def append(self, s):
        """Returns the SqlBuilder object appended specified raw SQL."""
        return SqlBuilder(self._encoding, self._sql + b" " + self._as_bytes(s))

    def from_tables(self, tables):
        """
        FROM clause
        
        tables: the table name or a list of the table names
        """

        if isinstance(tables, dict):
            tables = tables.items()
        elif not isinstance(tables, (list, tuple)):
            tables = [tables]
        return self.append(b"from " + b", ".join((self._quote_identifier(table[1]) + b" as " + self._quote_identifier(table[0])
            if isinstance(table, (list, tuple)) else self._quote_identifier(table)) for table in tables))
    
    def select(self, selector):
        """
        SELECT syntax

        selector: a list or dict of the column names or a function that returns a list or dict
                  example * lambda _: _ #equals "*"
                          * lambda _: _.column
                          * lambda _: _.now()
                          * lambda _: [_.column0, _.column1]
                          * lambda _: { "A": _.column0, "": _.column1 }
        """
        
        if isinstance(selector, (str, unicode, bytes)):
            return self.append(b"select " + self._as_bytes(selector))

        if isinstance(selector, (list, tuple, dict)):
            if isinstance(selector, dict):
                selector = selector.items()
            return self.append(b"select " + b", ".join((self._quote_identifier(column[1]) + b" as " + self._quote_identifier(column[0])
                if isinstance(column, (list, tuple)) else self._quote_identifier(column)) for column in selector))

        result = selector(SNameBase())
        if isinstance(result, (list, tuple, dict)):
            if isinstance(result, dict):
                result = result.items()
            select_expr = b", ".join((self._quote(obj[1]) + b" as " + self._quote_identifier(obj[0])
                if isinstance(obj, (list, tuple)) else self._quote(obj)) for obj in result)
        else:
            select_expr = self._quote(result)
        return self.append(b"select " + select_expr)
    
    def where(self, predicate):
        """
        WHERE clause

        predicate: a function that returns expression
                   example * lambda _: op_and(_.column0 > 5, _.column1 < 10)
        """

        if isinstance(predicate, (str, unicode, bytes)):
            return self.append(b"where " + self._as_bytes(predicate))

        return self.append(b"where " + self._quote(predicate(SNameBase())))

    def insert(self, into, columns=None, ignore=False):
        """
        INSERT syntax

        into   : the table name
        columns: a list of the column names
        ignore : add "IGNORE" to the SQL if true
        """

        result = b"insert"
        if ignore:
            result += b" ignore"
        result += b" into " + self._quote_identifier(into)
        if columns is not None:
            if isinstance(columns, (list, tuple)):
                result += b" (" + b", ".join(self._quote_identifier(s) for s in columns) + b")"
            else:
                raise TypeError()
        return self.append(result)

    def values(self, *values_list):
        """
        VALUES clause
        
        arguments: some lists of the values to insert or some functions that returns a list
        """

        if len(values_list) == 1 and isinstance(values_list[0], (str, unicode, bytes)):
            return self.append(b"values " + self._as_bytes(values_list[0]))

        return self.append(b"values " + b", ".join((b"(" + b", ".join(self._quote(value)
            for value in (arg if isinstance(arg, (list, tuple)) else arg(SNameBase()))) + b")") for arg in values_list))

    def set(self, pairs):
        """
        SET clause

        pairs: a dict of the column name and the value pairs or a function that returns a dict
        """

        if isinstance(pairs, (str, unicode, bytes)):
            return self.append(b"where " + self._as_bytes(pairs))

        return self.append(b"set " + b", ".join(self._quote_identifier(key) + b"=" + self._quote(value)
            for key, value in (pairs.items() if isinstance(pairs, dict) else
            (pairs if isinstance(pairs, (list, tuple)) else pairs(SNameBase()).items()))))

    def update(self, table, ignore=False):
        """
        UPDATE syntax

        table : the table name
        ignore: add "IGNORE" to the SQL if true
        """

        return self.append(b"update " + (b"ignore " if ignore else b"") + self._quote_identifier(table))

    def delete(self, from_tables, quick=False, ignore=False):
        """
        DELETE syntax

        from_tables: the table name or a list of the table names]
        quick      : add "QUICK" to the SQL if true
        ignore     : add "IGNORE" to the SQL if true
        """

        return self.append(b"delete" + (b" quick" if ignore else b"") + (b" ignore" if ignore else b"")).from_tables(from_tables) 

class SNameBase(object):
    def __getattr__(self, name):
        return SName([name])

class _SOperatable(object):
    import abc
    __metaclass__ = abc.ABCMeta

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

    @abc.abstractmethod
    def _to_bytes(self, builder):
        return b""

class SName(_SOperatable):
    def __init__(self, name_list):
        self.__name_list = list(name_list)

    def _to_bytes(self, builder):
        return b".".join(builder._quote_identifier(s) for s in self.__name_list)

    def __getattr__(self, name):
        return SName(self.__name_list + [name])

    def __call__(self, *args):
        return SMethod(self.__name_list, args)

class SMethod(_SOperatable):
    def __init__(self, name_list, args):
        self.__name_list = list(name_list)
        self.__args = args

    def _to_bytes(self, builder):
        return (b".".join([builder._quote_identifier(s) for s in self.__name_list[0:-1]] + [builder._as_bytes(self.__name_list[-1])]) + b"(" + b", ".join(builder._quote(arg) for arg in self.__args) + b")")

class SOperator(_SOperatable):
    def __init__(self, op_name, left, right):
        assert isinstance(op_name, (str, unicode))
        self.op_name = op_name
        self.left = left
        self.right = right

    def _to_bytes(self, builder):
        return b"(" + builder._quote(self.left) + b" " + builder._as_bytes(self.op_name) + b" " + builder._quote(self.right) + b")"

class SSingleOperator(_SOperatable):
    def __init__(self, op_name, expr):
        assert isinstance(op_name, (str, unicode))
        self.op_name = op_name
        self.expr = expr

    def _to_bytes(self, builder):
        return b"(" + builder._as_bytes(self.op_name) + b" " + builder._quote(self.expr) + b")"

class SHex(_SOperatable):
    def __init__(self, hex):
        import string
        if isinstance(hex, bytes):
            assert all(c in string.hexdigits.encode("ascii") for c in hex)
        elif isinstance(hex, (str, unicode)):
            assert all(c in string.hexdigits for c in hex)
        else:
            raise TypeError()
        self.hex = hex

    def _to_bytes(self, builder):
        return b"0x" + builder._as_bytes(self.hex)

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

def to_hex(value):
    """
    Convert bytes to 0x literal

    value: the bytes
    """
    
    try:
        hex = "".join("%02x" % b for b in value)
    except:
        hex = value.encode("hex")
    return SHex(hex)

def from_hex_str(value):
    """
    Make 0x literal from hex str

    value: a str of the hex
    """
    
    return SHex(value)
