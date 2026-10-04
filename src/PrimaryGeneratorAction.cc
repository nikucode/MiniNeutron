#include "PrimaryGeneratorAction.hh"

#include "G4Event.hh"
#include "G4Neutron.hh"
#include "G4ParticleGun.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"

PrimaryGeneratorAction::PrimaryGeneratorAction()
{
    // Queremos generar un neutrón por evento
    fParticleGun = new G4ParticleGun(1);

    // Elegimos la partícula: neutrón
    fParticleGun->SetParticleDefinition(
        G4Neutron::Definition()
    );

    // Energía inicial del neutrón
    fParticleGun->SetParticleEnergy(
        2.0 * MeV
    );

    // Posición inicial
    fParticleGun->SetParticlePosition(
        G4ThreeVector(0, 0, -30.0 * cm)
    );

    // Dirección: hacia +Z
    fParticleGun->SetParticleMomentumDirection(
        G4ThreeVector(0, 0, 1)
    );
}

PrimaryGeneratorAction::~PrimaryGeneratorAction()
{
    delete fParticleGun;
}

void PrimaryGeneratorAction::GeneratePrimaries(
    G4Event* event
)
{
    fParticleGun->GeneratePrimaryVertex(event);
}