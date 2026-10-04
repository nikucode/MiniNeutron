#include <ROOT/RDataFrame.hxx>
#include <TCanvas.h>
#include <TH1D.h>
#include <TH1I.h>
#include <TStyle.h>
#include <iostream>

void root_analysis()
{
    std::cout << "\n=== MiniNeutron ROOT analysis ===\n" << std::endl;

    const char* input_file =
        "results/runs/run_1000_tracks_v1/minineutron_tracks.root";

    ROOT::RDataFrame df("tracks", input_file);

    auto total_tracks = df.Count();

    auto captures =
        df.Filter("outcome == \"CAPTURE\"")
        .Count();

    auto inelastic =
        df.Filter("outcome == \"INELASTIC\"")
        .Count();

    auto escapes =
        df.Filter("outcome == \"ESCAPE\"")
        .Count();

    auto other =
        df.Filter("outcome == \"OTHER\"")
        .Count();


    std::cout
        << "Tracks primarios: "
        << total_tracks.GetValue()
        << std::endl;

    std::cout
        << "CAPTURE: "
        << captures.GetValue()
        << std::endl;

    std::cout
        << "INELASTIC: "
        << inelastic.GetValue()
        << std::endl;

    std::cout
        << "ESCAPE: "
        << escapes.GetValue()
        << std::endl;

    std::cout
        << "OTHER: "
        << other.GetValue()
        << std::endl;


    // ========================================================
    // HISTOGRAMA DE COLISIONES
    // ========================================================

    auto h_collisions = df.Histo1D(
        {
            "h_collisions",
            "MiniNeutron - Distribucion de colisiones;"
            "Numero de colisiones hadElastic;"
            "Tracks primarios",
            50,
            0,
            400
        },
        "collisions"
    );

    auto c1 =
        new TCanvas(
            "c1",
            "MiniNeutron collisions",
            800,
            600
        );

    gStyle->SetOptStat(0);

    h_collisions->Draw();

    c1->SaveAs(
        "results/figures/root_collisions_distribution.png"
    );


    // ========================================================
    // GRAFICO DE RESULTADOS FINALES
    // ========================================================

    auto h_outcomes =
        new TH1I(
            "h_outcomes",
            "MiniNeutron - Destino final de neutrones primarios;"
            "Resultado final;"
            "Numero de neutrones",
            4,
            0,
            4
        );

    h_outcomes
        ->GetXaxis()
        ->SetBinLabel(
            1,
            "CAPTURE"
        );

    h_outcomes
        ->GetXaxis()
        ->SetBinLabel(
            2,
            "INELASTIC"
        );

    h_outcomes
        ->GetXaxis()
        ->SetBinLabel(
            3,
            "ESCAPE"
        );

    h_outcomes
        ->GetXaxis()
        ->SetBinLabel(
            4,
            "OTHER"
        );


    h_outcomes->SetBinContent(
        1,
        captures.GetValue()
    );

    h_outcomes->SetBinContent(
        2,
        inelastic.GetValue()
    );

    h_outcomes->SetBinContent(
        3,
        escapes.GetValue()
    );

    h_outcomes->SetBinContent(
        4,
        other.GetValue()
    );


    auto c2 =
        new TCanvas(
            "c2",
            "MiniNeutron outcomes",
            800,
            600
        );

    gStyle->SetOptStat(0);

    h_outcomes->Draw("BAR");

    c2->SaveAs(
        "results/figures/root_primary_outcomes.png"
    );


    std::cout
        << "\nROOT analysis completed :3"
        << std::endl;
}