#include "G4RunManagerFactory.hh"
#include "G4UIExecutive.hh"
#include "G4UImanager.hh"
#include "G4VisExecutive.hh"

#include "QGSP_BIC_HP.hh"

#include "DetectorConstruction.hh"
#include "ActionInitialization.hh"


int main(int argc, char** argv)
{
    // ============================================================
    // RUN MANAGER
    // ============================================================

    auto* runManager =
        G4RunManagerFactory::CreateRunManager(
            G4RunManagerType::Serial
        );


    // ============================================================
    // USER INITIALIZATION
    // ============================================================

    runManager->SetUserInitialization(
        new DetectorConstruction()
    );

    runManager->SetUserInitialization(
        new QGSP_BIC_HP
    );

    runManager->SetUserInitialization(
        new ActionInitialization()
    );


    auto* uiManager =
        G4UImanager::GetUIpointer();


    // ============================================================
    // INTERACTIVE MODE
    //
    // ./minineutron
    // ============================================================

    if (argc == 1)
    {
        auto* visManager =
            new G4VisExecutive;

        visManager->Initialize();

        auto* ui =
            new G4UIExecutive(
                argc,
                argv
            );

        uiManager->ApplyCommand(
            "/run/initialize"
        );

        ui->SessionStart();

        delete ui;
        delete visManager;
    }


    // ============================================================
    // BATCH MODE
    //
    // ./minineutron macro.mac
    // ============================================================

    else
    {
        G4String command =
            "/control/execute ";

        G4String macroFile =
            argv[1];

        uiManager->ApplyCommand(
            command + macroFile
        );
    }


    // ============================================================
    // CLEANUP
    // ============================================================

    delete runManager;

    return 0;
}