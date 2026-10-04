#include "ActionInitialization.hh"

#include "PrimaryGeneratorAction.hh"
#include "SteppingAction.hh"

void ActionInitialization::Build() const
{
    SetUserAction(
        new PrimaryGeneratorAction()
    );
    
    SetUserAction(
        new SteppingAction()
    );
}