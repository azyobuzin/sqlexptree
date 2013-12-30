from sqlexptree import SqlBuilder, op_and, op_not, op_or, op_xor

print(SqlBuilder().select(lambda _: _.column0).from_tables("table").build())

print(SqlBuilder().select(lambda _: { "A": _.max(_.column0) + 5, "B": _.now() }).from_tables("table").build())

print(SqlBuilder()
      .select(lambda _: [_.column0, _.column1])
      .from_tables("table")
      .where(lambda _: op_and(_.column0 > 5, _.column1 < 10))
      .build())

input()
