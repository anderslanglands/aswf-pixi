#include <Imath/ImathFun.h>
#include <Imath/ImathVec.h>
#include <Imath/half.h>

int main()
{
    Imath::half value = 1.0f;
    Imath::V3f vector(1.0f, 2.0f, 3.0f);
    float next = Imath::succf(1.0f);

    return value == Imath::half(1.0f) && vector.length() > 0.0f && next > 1.0f ? 0 : 1;
}
