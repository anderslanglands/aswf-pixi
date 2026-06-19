#include <Partio.h>

#include <cmath>
#include <iostream>

namespace
{

int fail(const char* message)
{
    std::cerr << message << "\n";
    return 1;
}

bool near(float actual, float expected)
{
    return std::fabs(actual - expected) < 0.001f;
}

int check_file(const char* path)
{
    Partio::ParticlesDataMutable* read = Partio::read(path, false);
    if (!read) {
        return fail("failed to read particle file");
    }
    if (read->numParticles() != 1) {
        read->release();
        return fail("unexpected particle count");
    }

    Partio::ParticleAttribute read_position;
    if (!read->attributeInfo("position", read_position)) {
        read->release();
        return fail("missing position attribute");
    }
    const float* read_value = read->data<float>(read_position, 0);
    if (!near(read_value[0], 1.0f) || !near(read_value[1], 2.0f) || !near(read_value[2], 3.0f)) {
        read->release();
        return fail("unexpected position value");
    }

    read->release();
    return 0;
}

} // namespace

int main()
{
    Partio::ParticlesDataMutable* particles = Partio::create();
    if (!particles) {
        return fail("failed to create particle set");
    }

    Partio::ParticleAttribute position = particles->addAttribute("position", Partio::VECTOR, 3);
    Partio::ParticleIndex particle = particles->addParticle();
    float* value = particles->dataWrite<float>(position, particle);
    value[0] = 1.0f;
    value[1] = 2.0f;
    value[2] = 3.0f;

    Partio::write("partio_consumer.bgeo", *particles);
    Partio::write("partio_consumer_compressed.bgeo.gz", *particles, true);
    particles->release();

    int result = check_file("partio_consumer.bgeo");
    if (result != 0) {
        return result;
    }
    return check_file("partio_consumer_compressed.bgeo.gz");
}
