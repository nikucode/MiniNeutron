import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


# ============================================================
# 1. CARGAR DATOS
# ============================================================

csv_path = "../build/minineutron_steps.csv"

data = pd.read_csv(csv_path)

print("\n=== MiniNeutron primary-track analysis ===\n")

print("Numero total de filas:", len(data))
print("Numero de eventos:", data["event"].nunique())
print("Numero de tracks de neutron:", data[["event", "track_id"]].drop_duplicates().shape[0])


# ============================================================
# 2. SEPARAR LOS NEUTRONES PRIMARIOS
# ============================================================

# En Geant4:
#
# parent_id = 0
# significa que la particula fue generada directamente
# por nuestra fuente y no por otra particula.
#
# Actualmente generamos un neutron primario por evento.

primary = data[
    data["parent_id"] == 0
].copy()

print("\nFilas correspondientes a neutrones primarios:", len(primary))

print(
    "Tracks primarios:",
    primary[["event", "track_id"]]
    .drop_duplicates()
    .shape[0]
)


# ============================================================
# 3. COMPROBAR LOS TRACK ID PRIMARIOS
# ============================================================

primary_tracks = (
    primary[
        ["event", "track_id", "parent_id"]
    ]
    .drop_duplicates()
)

print("\nTracks primarios encontrados:")
print(primary_tracks.head(20))


# ============================================================
# 4. SELECCIONAR COLISIONES ELASTICAS DEL PRIMARIO
# ============================================================

elastic_primary = primary[
    primary["process"] == "hadElastic"
]

print(
    "\nNumero total de colisiones hadElastic de primarios:",
    len(elastic_primary)
)


# ============================================================
# 5. CONTAR COLISIONES POR TRACK PRIMARIO
# ============================================================

# Agrupamos por EVENTO y TRACK.
#
# Esto es mas correcto que agrupar solamente por evento,
# porque un evento puede contener multiples tracks.

collisions_per_track = (
    elastic_primary
    .groupby(["event", "track_id"])
    .size()
)


# Crear indice con TODOS los tracks primarios,
# incluyendo aquellos que tuvieron 0 colisiones.
all_primary_tracks = pd.MultiIndex.from_frame(
    primary[
        ["event", "track_id"]
    ]
    .drop_duplicates()
)


collisions_per_track = (
    collisions_per_track
    .reindex(
        all_primary_tracks,
        fill_value=0
    )
)

collisions_per_track.index.names = [
    "event",
    "track_id"
]


print(
    "\nPromedio de colisiones por track primario:",
    collisions_per_track.mean()
)

print(
    "Mediana de colisiones:",
    collisions_per_track.median()
)

print(
    "Minimo de colisiones:",
    collisions_per_track.min()
)

print(
    "Maximo de colisiones:",
    collisions_per_track.max()
)


# ============================================================
# 6. ENCONTRAR EL ULTIMO STEP DE CADA TRACK PRIMARIO
# ============================================================

last_step_primary = (
    primary
    .sort_values(
        ["event", "track_id", "step"]
    )
    .groupby(
        ["event", "track_id"]
    )
    .tail(1)
)


# Conservamos informacion importante del estado final
final_state = (
    last_step_primary[
        [
            "event",
            "track_id",
            "volume",
            "energy_after_MeV",
            "process",
            "step_status"
        ]
    ]
    .set_index(
        ["event", "track_id"]
    )
)


print("\nEstado final de los tracks primarios:")
print(final_state)


# ============================================================
# 7. CLASIFICAR EL RESULTADO FINAL
# ============================================================

def classify_outcome(row):

    # Captura neutronica
    if row["process"] == "nCaptureHP":
        return "CAPTURE"

    # Interaccion inelastica que termina el track primario
    if row["process"] == "neutronInelastic":
        return "INELASTIC"

    # Salida completa del mundo de simulacion
    if row["step_status"] == "WorldBoundary":
        return "ESCAPE"

    # Cualquier mecanismo que aun no hemos clasificado
    return "OTHER"


final_state["outcome"] = (
    final_state.apply(
        classify_outcome,
        axis=1
    )
)


print("\nClasificacion final:")
print(
    final_state[
        [
            "energy_after_MeV",
            "process",
            "step_status",
            "outcome"
        ]
    ]
)

# ============================================================
# 8. CONTAR RESULTADOS
# ============================================================

outcome_counts = (
    final_state["outcome"]
    .value_counts()
)

print("\nResultados finales:")
print(outcome_counts)


number_tracks = len(final_state)

number_capture = (
    outcome_counts.get("CAPTURE", 0)
)

number_inelastic = (
    outcome_counts.get("INELASTIC", 0)
)

number_escape = (
    outcome_counts.get("ESCAPE", 0)
)

number_other = (
    outcome_counts.get("OTHER", 0)
)

print(
    "\nCapturados:",
    number_capture,
    f"({number_capture / number_tracks * 100:.2f} %)"
)

print(
    "Terminacion por interaccion inelastica:",
    number_inelastic,
    f"({number_inelastic / number_tracks * 100:.2f} %)"
)

print(
    "Escaparon del mundo:",
    number_escape,
    f"({number_escape / number_tracks * 100:.2f} %)"
)

print(
    "Otros finales:",
    number_other,
    f"({number_other / number_tracks * 100:.2f} %)"
)


# ============================================================
# 9. CREAR RESUMEN POR TRACK PRIMARIO
# ============================================================

primary_summary = pd.DataFrame({
    "collisions": collisions_per_track,
    "final_energy_MeV": final_state["energy_after_MeV"],
    "final_process": final_state["process"],
    "final_step_status": final_state["step_status"],
    "outcome": final_state["outcome"]
})


print("\nResumen de tracks primarios:")
print(primary_summary)


# ============================================================
# 10. EVENTOS SIN COLISIONES ELASTICAS
# ============================================================

no_elastic = primary_summary[
    primary_summary["collisions"] == 0
]

print(
    "\nTracks primarios sin colisiones hadElastic:",
    len(no_elastic)
)

if len(no_elastic) > 0:
    print(no_elastic)


# ============================================================
# 11. ENERGIA FINAL
# ============================================================

print(
    "\nEnergia final media:",
    primary_summary["final_energy_MeV"].mean(),
    "MeV"
)

print(
    "Mediana de energia final:",
    primary_summary["final_energy_MeV"].median(),
    "MeV"
)


# ============================================================
# 12. GRAFICO:
# RESULTADO FINAL
# ============================================================

# Orden fijo para que los graficos sean faciles de comparar
outcome_order = [
    "CAPTURE",
    "INELASTIC",
    "ESCAPE",
    "OTHER"
]

outcome_plot = (
    outcome_counts
    .reindex(
        outcome_order,
        fill_value=0
    )
)

plt.figure()

plt.bar(
    outcome_plot.index,
    outcome_plot.values
)

plt.xlabel("Resultado final")
plt.ylabel("Numero de neutrones primarios")

plt.title(
    "MiniNeutron - Destino final de neutrones primarios"
)

plt.tight_layout()

output_path = (
    "../results/figures/"
    "primary_outcomes.png"
)

plt.savefig(
    output_path,
    dpi=300,
    bbox_inches="tight"
)

print("\nGrafico guardado:")
print(output_path)

plt.close()


# ============================================================
# 13. GRAFICO:
# COLISIONES VS ENERGIA FINAL
# ============================================================

plt.figure()

plt.scatter(
    primary_summary["collisions"],
    primary_summary["final_energy_MeV"]
)

plt.xlabel(
    "Numero de colisiones hadElastic"
)

plt.ylabel(
    "Energia final [MeV]"
)

plt.title(
    "MiniNeutron - Colisiones vs energia final del primario"
)

plt.tight_layout()

output_path = (
    "../results/figures/"
    "primary_collisions_vs_energy.png"
)

plt.savefig(
    output_path,
    dpi=300,
    bbox_inches="tight"
)

print("\nGrafico guardado:")
print(output_path)

plt.close()


# ============================================================
# 14. GRAFICO:
# ENERGIA FINAL EN ESCALA LOGARITMICA
# ============================================================

positive_energy = primary_summary[
    primary_summary["final_energy_MeV"] > 0
]["final_energy_MeV"]


if len(positive_energy) > 1:

    log_bins = np.logspace(
        np.log10(
            positive_energy.min()
        ),
        np.log10(
            positive_energy.max()
        ),
        50
    )

    plt.figure()

    plt.hist(
        positive_energy,
        bins=log_bins
    )

    plt.xscale("log")

    plt.xlabel(
        "Energia final [MeV]"
    )

    plt.ylabel(
        "Numero de neutrones primarios"
    )

    plt.title(
        "MiniNeutron - Energia final de primarios"
    )

    plt.tight_layout()

    output_path = (
        "../results/figures/"
        "primary_final_energy_log.png"
    )

    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )

    print("\nGrafico guardado:")
    print(output_path)

    plt.close()


# ============================================================
# 15. GUARDAR DATASET RESUMIDO
# ============================================================

summary_path = (
    "../results/"
    "primary_track_summary.csv"
)

primary_summary.to_csv(
    summary_path
)

print("\nResumen guardado en:")
print(summary_path)


# ============================================================
# 16. FIN
# ============================================================

print(
    "\nAnalisis de tracks primarios completado :3"
)