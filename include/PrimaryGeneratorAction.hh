#ifndef PrimaryGeneratorAction_h
#define PrimaryGeneratorAction_h

#include "G4VUserPrimaryGeneratorAction.hh"

class G4ParticleGun;
class G4Event;

class PrimaryGeneratorAction
    : public G4VUserPrimaryGeneratorAction
{
public:
    PrimaryGeneratorAction();
    ~PrimaryGeneratorAction() override;

    void GeneratePrimaries(G4Event* event) override;

private:
    G4ParticleGun* fParticleGun = nullptr;
};

#endif