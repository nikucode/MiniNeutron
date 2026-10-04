#include "DetectorConstruction.hh"

#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4SystemOfUnits.hh"
#include "G4VisAttributes.hh"


G4VPhysicalVolume* DetectorConstruction::Construct()
{
    auto* nist = G4NistManager::Instance();

    auto* air =
        nist->FindOrBuildMaterial("G4_AIR");

    auto* hdpe =
        nist->FindOrBuildMaterial("G4_POLYETHYLENE");
    
    G4double worldSize = 1.0 * m;

    auto* solidWorld =
        new G4Box(
            "World",
            worldSize / 2,
            worldSize / 2,
            worldSize / 2
        );

    auto* logicWorld =
        new G4LogicalVolume(
            solidWorld,
            air,
            "World"
        );
    
    logicWorld->SetVisAttributes(
        G4VisAttributes::GetInvisible()
    );

    auto* physWorld =
        new G4PVPlacement(
            nullptr,
            G4ThreeVector(),
            logicWorld,
            "World",
            nullptr,
            false,
            0,
            true
        );


G4double moderatorX = 20.0 * cm;
G4double moderatorY = 20.0 * cm;
G4double moderatorZ = 10.0 * cm;

auto* solidModerator =
    new G4Box(
        "Moderator",
        moderatorX / 2,
        moderatorY / 2,
        moderatorZ / 2
    );

auto* logicModerator =
    new G4LogicalVolume(
        solidModerator,
        hdpe,
        "Moderator"
    );

auto* moderatorVis =
    new G4VisAttributes();

moderatorVis->SetVisibility(true);

logicModerator->SetVisAttributes(
    moderatorVis
);


new G4PVPlacement(
    nullptr,
    G4ThreeVector(0, 0, 0),
    logicModerator,
    "Moderator",
    logicWorld,
    false,
    0,
    true
);

    return physWorld;
}