# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import List, Optional, Iterator, Tuple, Callable
import os
import shutil
import sys
import time

# ============================================================
#
# Utilitaires d'affichage (nettoyage + mise en page adaptée)
#
# ============================================================

def clear_screen() -> Tuple[int, int]:
    """
    Nettoie complètement le terminal et renvoie (cols, rows).
    - Utilise les séquences ANSI (compatibles macOS / Linux).
    - Adapte ensuite quelques largeurs à la fenêtre.
    """
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()
    size = shutil.get_terminal_size((100, 28))
    return size.columns, size.lines

def header(title: str) -> None:
    cols, _ = shutil.get_terminal_size((100, 28))
    print("=" * cols)
    print(title[:cols])
    print("=" * cols)

def pause(msg: str = "Entrée pour continuer...") -> None:
    try:
        input(msg)
    except EOFError:
        # Si l'entrée standard est close (rare), on temporise un peu
        time.sleep(0.8)

def ask_int(prompt: str) -> int:
    """Demande un entier à l'utilisateur (boucle tant que invalide)."""
    while True:
        try:
            s = input(prompt).strip()
            x = int(s)
            return x
        except ValueError:
            print("Valeur non valide. Merci d'entrer un entier (ex: 12, -3, 0).")

# ============================================================
#
# Banque de listes triées
#
# ============================================================

PRESET_BANK = {
    "notes":        [3, 5, 9, 9, 10, 12, 12, 14, 17, 18],
    "pairs_0_50":   list(range(0, 52, 2)),
    "carres_1_20":  [i*i for i in range(1, 21)],
    "progression":  list(range(10, 110, 5)),
    "doubles":      [1, 1, 2, 2, 2, 3, 3, 5, 8, 8, 13, 21],
}

# ============================================================
#
# Dessin de l'état du tableau (adapté à la largeur du terminal)
#
# ============================================================

def _slice_window(n: int, left: int, right: int, cols: int, min_cells: int = 8) -> Tuple[int, int]:
    """
    Choisit une fenêtre d'indices [i0, i1] à afficher pour rester lisible.
    On centre la fenêtre sur [left..right] si le tableau est très long.
    """
    # largeur par cellule (approx): "[val]" + espace ~ 6 à 8 chars typiques
    # on estime 6, puis on garde une marge
    cell_w = 6
    max_cells = max(min_cells, (cols - 8) // cell_w)  # 8 = marge
    if n <= max_cells:
        return 0, n - 1
    # On centre autour du segment utile
    seg_center = (left + right) // 2
    half = max_cells // 2
    i0 = max(0, seg_center - half)
    i1 = min(n - 1, i0 + max_cells - 1)
    # Ajuste si on est collé au bord
    if i1 - i0 + 1 < max_cells:
        i0 = max(0, i1 - max_cells + 1)
    return i0, i1

def draw_array(arr: List[int], left: int, right: int, mid: int, title: str, expl: str) -> None:
    cols, _ = shutil.get_terminal_size((100, 28))
    n = len(arr)
    i0, i1 = _slice_window(n, max(0,left), max(0,right), cols)

    # Titre
    header(title)

    # Légende
    legend = "L=gauche  M=milieu  R=droite"
    print(legend[:cols])
    print("-" * min(cols, 100))

    # Ligne valeurs
    values = []
    for i in range(i0, i1 + 1):
        s = str(arr[i])
        values.append(f"[{s}]")
    line_values = " ".join(values)
    print(line_values[:cols])

    # Ligne indices
    indices = []
    for i in range(i0, i1 + 1):
        indices.append(f" {i:>2} ")  # largeur 4~5
    print(" ".join(indices)[:cols])

    # Ligne marqueurs
    markers = []
    for i in range(i0, i1 + 1):
        mark = "   "
        if i == left == right == mid:
            mark = "LMR"
        elif i == left == right:
            mark = "LR "
        elif i == left == mid:
            mark = "LM "
        elif i == right == mid:
            mark = "MR "
        elif i == left:
            mark = "L  "
        elif i == right:
            mark = "R  "
        elif i == mid:
            mark = " M "
        markers.append(mark)
    print(" ".join(markers)[:cols])

    print("-" * min(cols, 100))
    # Explication (on tronque proprement si trop long)
    for paragraph in expl.split("\n"):
        print(paragraph[:cols])
    print()

# ============================================================
#
# Étapes d'algorithmes (générateurs)
#
# ============================================================

@dataclass
class Step:
    left: int
    right: int
    mid: int
    relation: str   # "<", ">", "==", "<=", ">=", "final"
    explanation: str
    done: bool = False
    payload: Optional[int] = None  # ex: index, position d'insertion

def steps_find_any(arr: List[int], x: int) -> Iterator[Step]:
    g, d = 0, len(arr) - 1
    while g <= d:
        m = (g + d) // 2
        if arr[m] == x:
            yield Step(g, d, m, "==", f"arr[mid]==x ({arr[m]}=={x}) → trouvé à l'indice {m}.",
                       done=True, payload=m)
            return
        elif arr[m] < x:
            yield Step(g, d, m, "<", f"{arr[m]} < {x} → on va à DROITE (g ← m+1 = {m+1}).")
            g = m + 1
        else:
            yield Step(g, d, m, ">", f"{arr[m]} > {x} → on va à GAUCHE (d ← m-1 = {m-1}).")
            d = m - 1
    yield Step(g, d, (g + d) // 2 if g+d>=0 else 0, "final", "Non trouvé.", done=True, payload=-1)

def steps_first_occurrence(arr: List[int], x: int) -> Iterator[Step]:
    g, d = 0, len(arr) - 1
    res = -1
    while g <= d:
        m = (g + d) // 2
        if arr[m] >= x:
            if arr[m] == x:
                res = m
                yield Step(g, d, m, "==", f"Trouvé {x} à {m}. On cherche encore plus à GAUCHE.", done=False)
            else:
                yield Step(g, d, m, ">=", f"{arr[m]} >= {x} sans égalité. On va à GAUCHE.")
            d = m - 1
        else:
            yield Step(g, d, m, "<", f"{arr[m]} < {x}. On va à DROITE.")
            g = m + 1
    yield Step(g, d, g, "final", f"Première occurrence = {res}.", done=True, payload=res)

def steps_last_occurrence(arr: List[int], x: int) -> Iterator[Step]:
    g, d = 0, len(arr) - 1
    res = -1
    while g <= d:
        m = (g + d) // 2
        if arr[m] <= x:
            if arr[m] == x:
                res = m
                yield Step(g, d, m, "==", f"Trouvé {x} à {m}. On cherche encore plus à DROITE.", done=False)
            else:
                yield Step(g, d, m, "<=", f"{arr[m]} <= {x} sans égalité. On va à DROITE.")
            g = m + 1
        else:
            yield Step(g, d, m, ">", f"{arr[m]} > {x}. On va à GAUCHE.")
            d = m - 1
    yield Step(g, d, d, "final", f"Dernière occurrence = {res}.", done=True, payload=res)

def steps_bisect_left(arr: List[int], x: int) -> Iterator[Step]:
    g, d = 0, len(arr)
    while g < d:
        m = (g + d) // 2
        if arr[m] < x:
            yield Step(g, d-1, m, "<", f"{arr[m]} < {x} → g ← m+1 = {m+1}.")
            g = m + 1
        else:
            yield Step(g, d-1, m, ">=", f"{arr[m]} >= {x} → d ← m = {m}.")
            d = m
    yield Step(g, d-1, g, "final", f"Position d'insertion (gauche) = {g}.", done=True, payload=g)

def steps_bisect_right(arr: List[int], x: int) -> Iterator[Step]:
    g, d = 0, len(arr)
    while g < d:
        m = (g + d) // 2
        if arr[m] <= x:
            yield Step(g, d-1, m, "<=", f"{arr[m]} <= {x} → g ← m+1 = {m+1}.")
            g = m + 1
        else:
            yield Step(g, d-1, m, ">", f"{arr[m]} > {x} → d ← m = {m}.")
            d = m
    yield Step(g, d-1, g, "final", f"Position d'insertion (droite) = {g}.", done=True, payload=g)

# ============================================================
#
# Enveloppes d'exécution (affichage pas à pas)
#
# ============================================================

def run_steps(arr: List[int], x: int, generator: Callable[[List[int], int], Iterator[Step]], title: str) -> Optional[int]:
    step_no = 1
    result = None
    for st in generator(arr, x):
        clear_screen()
        draw_array(arr, st.left, st.right, st.mid, f"{title} — Étape {step_no}", st.explanation)
        if st.done:
            result = st.payload
        step_no += 1
        pause("Entrée pour étape suivante...")
    clear_screen()
    header(title + " — Résultat")
    if result is None:
        print("Aucun résultat retourné.\n")
    else:
        print(f"=> Résultat: {result}\n")
    pause()
    return result

def run_count_occurrences(arr: List[int], x: int) -> None:
    title = f"Compter les occurrences de x={x}"
    # Première occurrence
    first = run_steps(arr, x, steps_first_occurrence, f"{title} (première occurrence)")
    # Dernière occurrence
    last = run_steps(arr, x, steps_last_occurrence, f"{title} (dernière occurrence)")
    clear_screen()
    header(title + " — Bilan")
    if first == -1 or first is None:
        print(f"x={x} absent : 0 occurrence.\nPlage = [-1, -1]\n")
    else:
        count = (0 if last is None or last < first else (last - first + 1))
        print(f"Plage: [{first}, {last}] → Nombre d'occurrences = {count}\n")
    pause()

def run_range_first_last(arr: List[int], x: int) -> None:
    title = f"Plage [première, dernière] pour x={x}"
    first = run_steps(arr, x, steps_first_occurrence, f"{title} (première)")
    last = run_steps(arr, x, steps_last_occurrence, f"{title} (dernière)")
    clear_screen()
    header(title + " — Bilan")
    if first == -1 or first is None:
        print(f"x={x} absent : [-1, -1]\n")
    else:
        print(f"Plage = [{first}, {last}]\n")
    pause()

# ============================================================
#
# Menus (liste + algo) — avec nettoyage à chaque écran
#
# ============================================================

def choose_list(bank: dict) -> List[int]:
    while True:
        clear_screen()
        header("LISTES TRIÉES DISPONIBLES")
        keys = sorted(bank.keys())
        for i, name in enumerate(keys, 1):
            print(f"  [{i}] {name:>12} : {bank[name]}")
        print("  [A] Ajouter une nouvelle liste triée")
        print("  [Q] Quitter")
        print()
        # Demander le choix de l'utilisateur
        choice = input("Ton choix [1..{n}, A, Q] : ".format(n=len(keys))).strip().lower()

        if choice == "q":
            sys.exit(0)
        if choice == "a":
            clear_screen()
            header("AJOUT D'UNE LISTE")
            print("Entrer des entiers séparés par des espaces (ex: 1 2 2 5 9).")
            # Lire la ligne
            raw = input(">> ").strip()
            try:
                # Convertir les entiers
                arr = [int(tok) for tok in raw.split()]
            except ValueError:
                print("\nMauvais format. Réessaie (ex: 0 1 1 2 3).")
                pause()
                continue
            # Trier
            arr.sort()
            # Nommer et stocker
            name = input("Nom pour cette liste : ").strip() or f"perso_{len(bank)+1}"
            bank[name] = arr
            print("\nListe ajoutée et triée :", arr)
            pause()
            return arr

        # choix numérique
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(keys):
                return bank[keys[idx-1]]
            else:
                print("Numéro invalide.")
                pause()
                continue

        print("Choix invalide.")
        pause()

def choose_algo() -> int:
    while True:
        clear_screen()
        header("CHOIX DE L'ALGORITHME")
        print("  [1] Présence (renvoie un index ou -1)")
        print("  [2] Première occurrence (lower bound == x)")
        print("  [3] Dernière occurrence (upper bound - 1 == x)")
        print("  [4] Point d'insertion gauche (bisect_left)")
        print("  [5] Point d'insertion droite (bisect_right)")
        print("  [6] Compter les occurrences")
        print("  [7] Plage [première, dernière]")
        print("  [Q] Retour")
        print()
        s = input("Ton choix : ").strip().lower()
        if s == "q":
            return 0
        if s.isdigit():
            k = int(s)
            if 1 <= k <= 7:
                return k
        print("Choix invalide.")
        pause()

# ============================================================
# Boucle principale
#
# L'utilisateur choisit une liste, puis un algo, puis on exécute
# l'algo pas à pas avec affichage.
#
# ============================================================

def main() -> None:
    bank = PRESET_BANK.copy()
    while True:
        arr = choose_list(bank)
        while True:
            clear_screen()
            header("LISTE COURANTE")
            print(arr, "\n")
            x = ask_int("Valeur recherchée / à insérer (entier) : ")
            algo = choose_algo()
            if algo == 0:
                break  # retour au choix de liste

            if len(arr) == 0:
                clear_screen()
                header("Cas particulier")
                print("La liste est vide.\n")
                if algo in (4, 5):
                    # bisect_left/right sur vide → 0
                    print("Résultat attendu = 0 (position d'insertion).")
                else:
                    print("Résultat attendu = -1 (absent).")
                pause()
                continue

            if algo == 1:
                run_steps(arr, x, steps_find_any, f"Recherche présence de {x}")
            elif algo == 2:
                run_steps(arr, x, steps_first_occurrence, f"Première occurrence de {x}")
            elif algo == 3:
                run_steps(arr, x, steps_last_occurrence, f"Dernière occurrence de {x}")
            elif algo == 4:
                run_steps(arr, x, steps_bisect_left, f"bisect_left pour {x}")
            elif algo == 5:
                run_steps(arr, x, steps_bisect_right, f"bisect_right pour {x}")
            elif algo == 6:
                run_count_occurrences(arr, x)
            elif algo == 7:
                run_range_first_last(arr, x)

            # Rejouer ?
            clear_screen()
            header("Encore ?")
            again = input("Tester un autre ALGO sur la même liste ? [o/N] : ").strip().lower()
            if again == "o":
                continue
            back = input("Changer de LISTE ? [o/N] : ").strip().lower()
            if back == "o":
                break
            print("\nFin. Merci à bientôt \n")
            return

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print("Interruption clavier. Ciao.")
