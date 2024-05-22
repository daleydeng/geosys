$include "common.mpl"

wgs84_to_gcj02 := proc(y, x)
    local a := 6378245.0
    ,ee := 0.00669342162296594323
    ,cx := x - 105.0
    ,cy := y - 35.0
    ,dy := -100.0 + 2.0 * cx + 3.0 * cy + 0.2 * cy * cy + 0.1 * cx * cy + 0.2 * sqrt(cx) + (20.0 * sin(6.0 * cx * Pi) + 20.0 * sin(2.0 * cx * Pi)) * 2.0 / 3.0 + (20.0 * sin(cy * Pi) + 40.0 * sin(cy / 3.0 * Pi)) * 2.0 / 3.0 + (160.0 * sin(cy / 12.0 * Pi) + 320 * sin(cy * Pi / 30.0)) * 2.0 / 3.0
    ,dx := 300.0 + cx + 2.0 * cy + 0.1 * cx * cx + 0.1 * cx * cy + 0.1 * sqrt(cx) + (20.0 * sin(6.0 * cx * Pi) + 20.0 * sin(2.0 * cx * Pi)) * 2.0 / 3.0 + (20.0 * sin(cx * Pi) + 40.0 * sin(cx / 3.0 * Pi)) * 2.0 / 3.0 + (150.0 * sin(cx / 12.0 * Pi) + 300.0 * sin(cx / 30.0 * Pi)) * 2.0 / 3.0
    ,ry := rad(y)
    ,magic := 1 - ee * sqr(sin(ry))
    ,sqrt_magic := sqrt(magic)
    ;
    dy := (dy * 180.0) / ((a * (1 - ee)) / (magic * sqrt_magic) * Pi);
    dx := (dx * 180.0) / (a / sqrt_magic * cos(ry) * Pi);
    [y + dy, x + dx];
end:

macro(code_tpl =
      proc(y, x, ret::vecf)
          ret := expr;
      end):
gencode('wgs84_to_gcj02', code_tpl,
        {expr=wgs84_to_gcj02(y, x)}):

wgs84_to_gcj02_jac := proc(y, x)
    mat2list(jacob(wgs84_to_gcj02(y, x), [y, x]));
end:


gencode('wgs84_to_gcj02_jac', code_tpl,
        {expr=wgs84_to_gcj02_jac(y, x)}):

X_PI := Pi * 3000.0 / 180.0:
gcj02_to_bd09 := proc(y, x)
    local z := sqrt(x * x + y * y) + 0.00002 * sin(y * X_PI)
    ,theta := arctan(y, x) + 0.000003 * cos(x * X_PI)
    ;
    [z * sin(theta) + 0.006, z * cos(theta) + 0.0065];
end:

gencode('gcj02_to_bd09', code_tpl,
        {expr=gcj02_to_bd09(y, x)}):

bd09_to_gcj02 :=  proc(y, x)
    local cx := x - 0.0065
    ,cy := y - 0.006
    ,z := sqrt(cx * cx + cy * cy) - 0.00002 * sin(cy * X_PI)
    ,theta := arctan(cy, cx) - 0.000003 * cos(cx * X_PI)
    ;
    [z * sin(theta), z * cos(theta)];
end:

gencode('bd09_to_gcj02', code_tpl,
        {expr=bd09_to_gcj02(y, x)}):
