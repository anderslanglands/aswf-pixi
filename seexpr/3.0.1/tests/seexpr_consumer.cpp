#include <SeExpr2/Expression.h>

#include <stdexcept>

int main()
{
    SeExpr2::Expression expr("1+2");
    if (!expr.isValid()) {
        throw std::runtime_error(expr.parseError());
    }

    const double* value = expr.evalFP();
    if (value[0] != 3.0) {
        throw std::runtime_error("unexpected SeExpr evaluation result");
    }

    return 0;
}
