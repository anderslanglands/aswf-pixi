#include <openvdb/openvdb.h>
#include <openvdb/io/File.h>
#include <openvdb/tools/LevelSetSphere.h>

#include <cmath>
#include <iostream>
#include <memory>
#include <string>

int main(int argc, char** argv)
{
    const std::string path = argc > 1 ? argv[1] : "openvdb-consumer.vdb";

    openvdb::initialize();

    openvdb::FloatGrid::Ptr grid = openvdb::tools::createLevelSetSphere<openvdb::FloatGrid>(
        2.0f, openvdb::Vec3f(0.0f), 0.5f, 3.0f, false);
    grid->setName("density");
    grid->tree().setValue(openvdb::Coord(1, 2, 3), 4.0f);

    openvdb::GridPtrVec grids;
    grids.push_back(grid);

    openvdb::io::File output(path);
    output.write(grids);
    output.close();

    openvdb::io::File input(path);
    input.open(false);
    openvdb::FloatGrid::Ptr readGrid = openvdb::gridPtrCast<openvdb::FloatGrid>(
        input.readGrid("density"));
    input.close();

    if (!readGrid) {
        std::cerr << "failed to read density grid from " << path << "\n";
        return 1;
    }

    const float value = readGrid->tree().getValue(openvdb::Coord(1, 2, 3));
    return std::abs(value - 4.0f) < 0.001f ? 0 : 1;
}
