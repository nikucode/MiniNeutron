#include "SteppingAction.hh"

#include "G4Step.hh"
#include "G4StepPoint.hh"
#include "G4StepStatus.hh"
#include "G4Track.hh"
#include "G4Event.hh"
#include "G4EventManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4VProcess.hh"
#include "G4SystemOfUnits.hh"
#include "G4UnitsTable.hh"
#include "G4ios.hh"

#include <fstream>


// ============================================================
// CONFIGURACION
// ============================================================

// true  -> muestra cada step en la terminal
// false -> modo experimento: guarda CSV sin llenar la terminal
constexpr bool PRINT_STEPS = false;


// ============================================================
// FUNCION AUXILIAR:
// CONVERTIR G4StepStatus A TEXTO
// ============================================================

G4String StepStatusName(G4StepStatus status)
{
    switch (status)
    {
        case fWorldBoundary:
            return "WorldBoundary";

        case fGeomBoundary:
            return "GeomBoundary";

        case fAtRestDoItProc:
            return "AtRestDoItProc";

        case fAlongStepDoItProc:
            return "AlongStepDoItProc";

        case fPostStepDoItProc:
            return "PostStepDoItProc";

        case fUserDefinedLimit:
            return "UserDefinedLimit";

        case fExclusivelyForcedProc:
            return "ExclusivelyForcedProc";

        case fUndefined:
        default:
            return "Undefined";
    }
}


// ============================================================
// STEPPING ACTION
// ============================================================

void SteppingAction::UserSteppingAction(const G4Step* step)
{
    const auto* track = step->GetTrack();


    // ========================================================
    // 1. FILTRAR SOLO NEUTRONES
    // ========================================================

    // Por ahora MiniNeutron registra solamente tracks
    // correspondientes a neutrones.
    if (
        track->GetParticleDefinition()->GetParticleName()
        != "neutron"
    )
    {
        return;
    }


    // ========================================================
    // 2. OBTENER LOS PUNTOS PRE Y POST STEP
    // ========================================================

    const auto* preStep =
        step->GetPreStepPoint();

    const auto* postStep =
        step->GetPostStepPoint();


    // ========================================================
    // 3. NUMERO DE EVENTO
    // ========================================================

    const auto* event =
        G4EventManager::GetEventManager()
        ->GetConstCurrentEvent();

    G4int eventID =
        event ? event->GetEventID() : -1;


    // ========================================================
    // 4. TRACK ID Y PARENT ID
    // ========================================================

    // track_id identifica una trayectoria individual
    // dentro del evento.
    G4int trackID =
        track->GetTrackID();

    // parent_id indica que track genero al actual.
    //
    // parent_id = 0
    // significa que el track corresponde a una
    // particula primaria generada por nuestra fuente.
    G4int parentID =
        track->GetParentID();


    // ========================================================
    // 5. NUMERO DE STEP
    // ========================================================

    G4int stepNumber =
        track->GetCurrentStepNumber();


    // ========================================================
    // 6. VOLUMEN ACTUAL
    // ========================================================

    auto* volume =
        preStep->GetTouchableHandle()->GetVolume();

    G4String volumeName = "Outside";

    if (volume)
    {
        volumeName = volume->GetName();
    }


    // ========================================================
    // 7. POSICION
    // ========================================================

    G4ThreeVector position =
        preStep->GetPosition();


    // ========================================================
    // 8. ENERGIA ANTES Y DESPUES
    // ========================================================

    G4double energyBefore =
        preStep->GetKineticEnergy();

    G4double energyAfter =
        postStep->GetKineticEnergy();

    G4double deltaEnergy =
        energyBefore - energyAfter;


    // ========================================================
    // 9. PROCESO FISICO
    // ========================================================

    G4String processName = "None";

    if (postStep->GetProcessDefinedStep())
    {
        processName =
            postStep
            ->GetProcessDefinedStep()
            ->GetProcessName();
    }


    // ========================================================
    // 10. ESTADO DEL STEP
    // ========================================================

    // Esto nos permite distinguir, por ejemplo:
    //
    // GeomBoundary  -> cruce entre volumenes
    // WorldBoundary -> salida del mundo de simulacion
    // PostStepDoItProc -> step terminado por un proceso fisico
    //
    G4StepStatus stepStatus =
        postStep->GetStepStatus();

    G4String stepStatusName =
        StepStatusName(stepStatus);


    // ========================================================
    // 11. GUARDAR DATOS EN CSV
    // ========================================================

    static std::ofstream csvFile(
        "minineutron_steps.csv"
    );

    static bool headerWritten = false;

    if (!headerWritten)
    {
        csvFile
            << "event,"
            << "track_id,"
            << "parent_id,"
            << "step,"
            << "volume,"
            << "x_mm,"
            << "y_mm,"
            << "z_mm,"
            << "energy_before_MeV,"
            << "energy_after_MeV,"
            << "delta_energy_MeV,"
            << "process,"
            << "step_status"
            << G4endl;

        headerWritten = true;
    }


    csvFile
        << eventID << ","
        << trackID << ","
        << parentID << ","
        << stepNumber << ","
        << volumeName << ","
        << position.x() / mm << ","
        << position.y() / mm << ","
        << position.z() / mm << ","
        << energyBefore / MeV << ","
        << energyAfter / MeV << ","
        << deltaEnergy / MeV << ","
        << processName << ","
        << stepStatusName
        << G4endl;


    // ========================================================
    // 12. MODO DEPURACION OPCIONAL
    // ========================================================

    if (PRINT_STEPS)
    {
        G4cout

            << "Event: "
            << eventID

            << " | Track: "
            << trackID

            << " | Parent: "
            << parentID

            << " | Step: "
            << stepNumber

            << " | Volume: "
            << volumeName

            << " | Position: ("
            << G4BestUnit(
                position.x(),
                "Length"
            )
            << ", "
            << G4BestUnit(
                position.y(),
                "Length"
            )
            << ", "
            << G4BestUnit(
                position.z(),
                "Length"
            )
            << ")"

            << " | E before: "
            << G4BestUnit(
                energyBefore,
                "Energy"
            )

            << " | E after: "
            << G4BestUnit(
                energyAfter,
                "Energy"
            )

            << " | Process: "
            << processName

            << " | Step status: "
            << stepStatusName

            << G4endl;
    }
}