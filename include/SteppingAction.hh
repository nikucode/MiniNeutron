#ifndef SteppingAction_h
#define SteppingAction_h

#include "G4UserSteppingAction.hh"

class G4Step;

class SteppingAction : public G4UserSteppingAction
{
public:
    SteppingAction() = default;
    ~SteppingAction() override = default;

    void UserSteppingAction(const G4Step* step) override;
};

#endif