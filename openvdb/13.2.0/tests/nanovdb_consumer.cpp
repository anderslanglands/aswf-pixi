#include <nanovdb/GridHandle.h>
#include <nanovdb/NanoVDB.h>
#include <nanovdb/tools/CreatePrimitives.h>

int main()
{
    auto handle = nanovdb::tools::createLevelSetSphere<float>(
        2.0f, nanovdb::Vec3d(0.0), 0.5, 3.0);
    const nanovdb::FloatGrid* grid = handle.grid<float>();
    if (!grid) return 1;

    const nanovdb::Coord ijk(1, 0, 0);
    const float value = grid->tree().getValue(ijk);
    return value < 0.0f ? 0 : 1;
}
