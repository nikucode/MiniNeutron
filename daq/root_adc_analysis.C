#include <ROOT/RDataFrame.hxx>

#include <TCanvas.h>
#include <TFile.h>
#include <TGraph.h>
#include <TH1D.h>

#include <iostream>
#include <vector>

void root_adc_analysis()
{
    const std::string input =
        "daq/data/simulated_adc.csv";

    std::cout << "\nMiniNeutron DAQ Bench - ROOT Analysis\n";
    std::cout << "input: " << input << "\n\n";

    auto df = ROOT::RDF::FromCSV(input);

    const auto nSamples = *df.Count();

    const auto meanVoltage = *df.Mean<double>("voltage_V");
    const auto minVoltage = *df.Min<double>("voltage_V");
    const auto maxVoltage = *df.Max<double>("voltage_V");

    const auto meanADC = *df.Mean<Long64_t>("adc_raw");
    const auto minADC = *df.Min<Long64_t>("adc_raw");
    const auto maxADC = *df.Max<Long64_t>("adc_raw");

    std::cout << "samples: " << nSamples << "\n\n";

    std::cout << "Voltage\n";
    std::cout << "mean: " << meanVoltage << " V\n";
    std::cout << "min:  " << minVoltage << " V\n";
    std::cout << "max:  " << maxVoltage << " V\n\n";

    std::cout << "ADC\n";
    std::cout << "mean: " << meanADC << "\n";
    std::cout << "min:  " << minADC << "\n";
    std::cout << "max:  " << maxADC << "\n";

    // --------------------------------------------------
    // ADC histogram
    // --------------------------------------------------

    auto histADC = df.Histo1D(
        {
            "h_adc",
            "MiniNeutron DAQ Bench - ADC Distribution;ADC raw value;Counts",
            40,
            250,
            800
        },
        "adc_raw"
    );

    TCanvas cADC(
        "c_adc",
        "ADC Distribution",
        900,
        600
    );

    histADC->Draw();

    cADC.SaveAs(
        "daq/data/root_adc_histogram.png"
    );

    // --------------------------------------------------
    // Voltage vs time
    // --------------------------------------------------

    auto timestamps = df.Take<double>("timestamp_s");
    auto voltages = df.Take<double>("voltage_V");

    TGraph graph(
        timestamps->size(),
        timestamps->data(),
        voltages->data()
    );

    graph.SetTitle(
        "MiniNeutron DAQ Bench - Voltage vs Time;"
        "Time [s];Voltage [V]"
    );

    TCanvas cVoltage(
        "c_voltage",
        "Voltage vs Time",
        1000,
        600
    );

    graph.Draw("AL");

    cVoltage.SaveAs(
        "daq/data/root_voltage_vs_time.png"
    );

    // --------------------------------------------------
    // Save analysis objects to ROOT file
    // --------------------------------------------------

    TFile output(
        "daq/data/minineutron_daq.root",
        "RECREATE"
    );

    histADC->Write();
    graph.Write("voltage_vs_time");

    output.Close();

    std::cout << "\nGenerated:\n";
    std::cout << "daq/data/root_adc_histogram.png\n";
    std::cout << "daq/data/root_voltage_vs_time.png\n";
    std::cout << "daq/data/minineutron_daq.root\n";
}