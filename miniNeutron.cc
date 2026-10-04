#include "G4RunManagerFactory.hh"
#include "G4UIExecutive.hh"
#include "G4UImanager.hh"
#include "G4VisExecutive.hh"

#include "QGSP_BIC_HP.hh"

#include "DetectorConstruction.hh"
#include "ActionInitialization.hh"

int main(int argc, char** argv)
{
    auto* runManager =
        G4RunManagerFactory::CreateRunManager(
            G4RunManagerType::Serial
        );

    runManager->SetUserInitialization(
        new DetectorConstruction()
    );

    runManager->SetUserInitialization(
        new QGSP_BIC_HP
    );

    runManager->SetUserInitialization(
        new ActionInitialization()
    );

    auto* visManager = new G4VisExecutive;
    visManager->Initialize();

    auto* ui = new G4UIExecutive(argc, argv);

    auto* uiManager =
        G4UImanager::GetUIpointer();

    uiManager->ApplyCommand("/run/initialize");

    ui->SessionStart();

    delete ui;
    delete visManager;
    delete runManager;

    return 0;
}