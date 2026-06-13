"""DB layer — Supabase Python client (pure Python, no C compilation needed)."""
from __future__ import annotations
import re
import streamlit as st
from supabase import create_client, Client

# ── Exercise programs for routine templates ───────────────────────────────────

def _ex(d, o, n, s, r, cat, pos=False, ank=False):
    return {"day_name": d, "order_index": o, "exercise_name": n,
            "sets": str(s), "reps": str(r), "category": cat,
            "is_posture": pos, "is_ankle": ank}

_TMPL_EXERCISES: dict[str, list[dict]] = {

"Fuerza Base 3x/sem": [
    _ex("Día A", 1, "Sentadilla", 3, "5", "piernas"),
    _ex("Día A", 2, "Press banca", 3, "5", "pecho"),
    _ex("Día A", 3, "Remo con barra", 3, "5", "espalda"),
    _ex("Día A", 4, "Face pull en polea", 3, "12-15", "hombros", pos=True),
    _ex("Día B", 1, "Sentadilla", 3, "5", "piernas"),
    _ex("Día B", 2, "Press militar", 3, "5", "hombros"),
    _ex("Día B", 3, "Peso muerto", 1, "5", "espalda"),
    _ex("Día B", 4, "Plancha", 3, "30s", "core", pos=True),
],

"Fuerza Intermedia 4x/sem": [
    _ex("Upper A", 1, "Press banca", 4, "6-8", "pecho"),
    _ex("Upper A", 2, "Remo con barra", 4, "6-8", "espalda"),
    _ex("Upper A", 3, "Press militar", 3, "6-8", "hombros"),
    _ex("Upper A", 4, "Jalón al pecho", 3, "8-10", "espalda"),
    _ex("Upper A", 5, "Face pull en polea", 3, "12-15", "hombros", pos=True),
    _ex("Upper A", 6, "Extensión tríceps polea", 3, "10-12", "brazos"),
    _ex("Lower A", 1, "Sentadilla", 4, "6-8", "piernas"),
    _ex("Lower A", 2, "Peso muerto rumano", 3, "8-10", "piernas"),
    _ex("Lower A", 3, "Prensa de piernas", 3, "10-12", "piernas"),
    _ex("Lower A", 4, "Curl femoral máquina", 3, "10-12", "piernas"),
    _ex("Lower A", 5, "Hip thrust", 3, "10-12", "piernas", pos=True),
    _ex("Upper B", 1, "Press inclinado mancuernas", 4, "8-10", "pecho"),
    _ex("Upper B", 2, "Dominadas (o jalón)", 4, "6-8", "espalda"),
    _ex("Upper B", 3, "Dips en paralelas", 3, "8-10", "pecho"),
    _ex("Upper B", 4, "Remo con mancuerna", 3, "8-10", "espalda"),
    _ex("Upper B", 5, "Curl bíceps barra", 3, "8-10", "brazos"),
    _ex("Lower B", 1, "Peso muerto", 4, "4-6", "espalda"),
    _ex("Lower B", 2, "Sentadilla búlgara", 3, "8-10", "piernas"),
    _ex("Lower B", 3, "Extensión cuádriceps máquina", 3, "12-15", "piernas"),
    _ex("Lower B", 4, "Abducción de cadera máquina", 3, "12-15", "piernas", pos=True),
    _ex("Lower B", 5, "Elevación de gemelos de pie", 4, "12-15", "piernas"),
],

"Powerlifting 5x/sem": [
    _ex("Sentadilla A", 1, "Sentadilla competición", 5, "5", "piernas"),
    _ex("Sentadilla A", 2, "Prensa de piernas", 4, "8-10", "piernas"),
    _ex("Sentadilla A", 3, "Extensión cuádriceps", 3, "12", "piernas"),
    _ex("Sentadilla A", 4, "Curl femoral tumbado", 3, "12", "piernas"),
    _ex("Press A", 1, "Press banca competición", 5, "5", "pecho"),
    _ex("Press A", 2, "Press banca con pausa", 4, "3", "pecho"),
    _ex("Press A", 3, "JM Press", 3, "6-8", "brazos"),
    _ex("Press A", 4, "Extensión tríceps polea", 4, "10-12", "brazos"),
    _ex("Press A", 5, "Face pull en polea", 3, "15", "hombros", pos=True),
    _ex("Sentadilla B", 1, "Sentadilla con pausa", 4, "3", "piernas"),
    _ex("Sentadilla B", 2, "Front squat", 3, "5", "piernas"),
    _ex("Sentadilla B", 3, "Good morning", 3, "8", "espalda"),
    _ex("Sentadilla B", 4, "Plancha", 3, "45s", "core", pos=True),
    _ex("Peso muerto", 1, "Peso muerto competición", 5, "3-5", "espalda"),
    _ex("Peso muerto", 2, "Peso muerto sumo", 3, "5", "espalda"),
    _ex("Peso muerto", 3, "Hiperextensiones", 3, "10-12", "espalda"),
    _ex("Peso muerto", 4, "Remo con barra Pendlay", 4, "6", "espalda"),
    _ex("Accesorios", 1, "Remo en polea baja", 3, "10-12", "espalda"),
    _ex("Accesorios", 2, "Dominadas lastre", 3, "6-8", "espalda"),
    _ex("Accesorios", 3, "Curl bíceps barra", 3, "10-12", "brazos"),
    _ex("Accesorios", 4, "Elevaciones laterales", 3, "15", "hombros"),
    _ex("Accesorios", 5, "Face pull en polea", 3, "15", "hombros", pos=True),
],

"Hipertrofia Push/Pull/Legs": [
    _ex("Push A", 1, "Press banca plana", 4, "8-12", "pecho"),
    _ex("Push A", 2, "Press inclinado mancuernas", 3, "10-12", "pecho"),
    _ex("Push A", 3, "Press hombro mancuernas", 3, "10-12", "hombros"),
    _ex("Push A", 4, "Elevaciones laterales", 3, "12-15", "hombros"),
    _ex("Push A", 5, "Extensión tríceps polea cuerda", 3, "12-15", "brazos"),
    _ex("Push A", 6, "Fondos banco tríceps", 3, "12-15", "brazos"),
    _ex("Pull A", 1, "Dominadas agarre prono", 4, "8-10", "espalda"),
    _ex("Pull A", 2, "Remo con barra", 3, "8-12", "espalda"),
    _ex("Pull A", 3, "Jalón al pecho agarre neutro", 3, "10-12", "espalda"),
    _ex("Pull A", 4, "Face pull en polea", 3, "15-20", "hombros", pos=True),
    _ex("Pull A", 5, "Curl bíceps barra", 3, "10-12", "brazos"),
    _ex("Pull A", 6, "Curl martillo mancuernas", 3, "12", "brazos"),
    _ex("Legs A", 1, "Sentadilla", 4, "8-12", "piernas"),
    _ex("Legs A", 2, "Prensa de piernas", 3, "10-12", "piernas"),
    _ex("Legs A", 3, "Extensión cuádriceps", 3, "12-15", "piernas"),
    _ex("Legs A", 4, "Curl femoral tumbado", 3, "12-15", "piernas"),
    _ex("Legs A", 5, "Hip thrust", 3, "10-12", "piernas", pos=True),
    _ex("Legs A", 6, "Elevación de gemelos", 4, "15-20", "piernas"),
    _ex("Push B", 1, "Press hombro barra militar", 4, "8-10", "hombros"),
    _ex("Push B", 2, "Aperturas con mancuernas banco plano", 3, "12-15", "pecho"),
    _ex("Push B", 3, "Dips en paralelas", 3, "10-12", "pecho"),
    _ex("Push B", 4, "Elevaciones frontales", 3, "12-15", "hombros"),
    _ex("Push B", 5, "Extensión tríceps mancuerna sobre cabeza", 3, "12", "brazos"),
    _ex("Pull B", 1, "Remo con barra Pendlay", 4, "6-8", "espalda"),
    _ex("Pull B", 2, "Jalón agarre supino", 3, "10-12", "espalda"),
    _ex("Pull B", 3, "Remo cara en polea", 3, "15", "hombros", pos=True),
    _ex("Pull B", 4, "Curl predicador mancuerna", 3, "10-12", "brazos"),
    _ex("Pull B", 5, "Curl concentración", 3, "12", "brazos"),
    _ex("Legs B", 1, "Peso muerto rumano", 4, "8-10", "piernas"),
    _ex("Legs B", 2, "Sentadilla búlgara", 3, "10-12", "piernas"),
    _ex("Legs B", 3, "Abducción de cadera máquina", 3, "15", "piernas", pos=True),
    _ex("Legs B", 4, "Zancada caminando", 3, "12/lado", "piernas"),
    _ex("Legs B", 5, "Elevación de gemelos sentado", 4, "15-20", "piernas"),
],

"Hipertrofia Full Body 3x": [
    _ex("Día A", 1, "Sentadilla", 3, "8-10", "piernas"),
    _ex("Día A", 2, "Press banca plana", 3, "8-10", "pecho"),
    _ex("Día A", 3, "Remo con barra", 3, "8-10", "espalda"),
    _ex("Día A", 4, "Press militar", 3, "10-12", "hombros"),
    _ex("Día A", 5, "Curl bíceps barra", 3, "10-12", "brazos"),
    _ex("Día A", 6, "Extensión tríceps polea", 3, "10-12", "brazos"),
    _ex("Día B", 1, "Peso muerto", 3, "6-8", "espalda"),
    _ex("Día B", 2, "Press inclinado mancuernas", 3, "10-12", "pecho"),
    _ex("Día B", 3, "Jalón al pecho", 3, "10-12", "espalda"),
    _ex("Día B", 4, "Zancadas alternas", 3, "10/lado", "piernas"),
    _ex("Día B", 5, "Elevaciones laterales", 3, "12-15", "hombros"),
    _ex("Día B", 6, "Plancha", 3, "30-45s", "core", pos=True),
    _ex("Día C", 1, "Prensa de piernas", 3, "10-12", "piernas"),
    _ex("Día C", 2, "Dips en paralelas", 3, "10-12", "pecho"),
    _ex("Día C", 3, "Remo con mancuerna", 3, "10-12", "espalda"),
    _ex("Día C", 4, "Hip thrust", 3, "12-15", "piernas", pos=True),
    _ex("Día C", 5, "Elevaciones laterales mancuernas", 3, "12-15", "hombros"),
    _ex("Día C", 6, "Face pull en polea", 3, "15", "hombros", pos=True),
],

"Hipertrofia Upper/Lower": [
    _ex("Upper A", 1, "Press banca plana", 4, "6-10", "pecho"),
    _ex("Upper A", 2, "Remo con barra", 4, "6-10", "espalda"),
    _ex("Upper A", 3, "Press inclinado mancuernas", 3, "10-12", "pecho"),
    _ex("Upper A", 4, "Jalón al pecho", 3, "10-12", "espalda"),
    _ex("Upper A", 5, "Face pull", 3, "15", "hombros", pos=True),
    _ex("Upper A", 6, "Curl bíceps barra", 3, "10-12", "brazos"),
    _ex("Upper A", 7, "Extensión tríceps polea", 3, "10-12", "brazos"),
    _ex("Lower A", 1, "Sentadilla", 4, "6-10", "piernas"),
    _ex("Lower A", 2, "Peso muerto rumano", 3, "8-10", "piernas"),
    _ex("Lower A", 3, "Prensa piernas pie alto", 3, "10-12", "piernas"),
    _ex("Lower A", 4, "Curl femoral máquina", 3, "10-12", "piernas"),
    _ex("Lower A", 5, "Elevación de gemelos de pie", 4, "12-15", "piernas"),
    _ex("Upper B", 1, "Press hombro mancuernas", 4, "8-10", "hombros"),
    _ex("Upper B", 2, "Dominadas o jalón supino", 4, "8-10", "espalda"),
    _ex("Upper B", 3, "Aperturas pecho polea", 3, "12-15", "pecho"),
    _ex("Upper B", 4, "Remo cara en polea", 3, "15", "hombros", pos=True),
    _ex("Upper B", 5, "Curl predicador", 3, "10-12", "brazos"),
    _ex("Upper B", 6, "Fondos tríceps banco", 3, "12", "brazos"),
    _ex("Lower B", 1, "Peso muerto", 4, "4-6", "espalda"),
    _ex("Lower B", 2, "Sentadilla búlgara", 3, "8-10", "piernas"),
    _ex("Lower B", 3, "Extensión cuádriceps", 3, "12-15", "piernas"),
    _ex("Lower B", 4, "Hip thrust barra", 3, "10-12", "piernas", pos=True),
    _ex("Lower B", 5, "Abducción de cadera máquina", 3, "12-15", "piernas", pos=True),
],

"Hipertrofia Torso/Pierna": [
    _ex("Torso A", 1, "Press banca plana", 4, "6-10", "pecho"),
    _ex("Torso A", 2, "Remo con barra", 4, "6-10", "espalda"),
    _ex("Torso A", 3, "Press inclinado barra", 3, "8-10", "pecho"),
    _ex("Torso A", 4, "Jalón al pecho agarre ancho", 3, "8-10", "espalda"),
    _ex("Torso A", 5, "Elevaciones laterales", 3, "12-15", "hombros"),
    _ex("Pierna A", 1, "Sentadilla", 4, "8-10", "piernas"),
    _ex("Pierna A", 2, "Peso muerto rumano", 3, "8-10", "piernas"),
    _ex("Pierna A", 3, "Prensa de piernas", 3, "10-12", "piernas"),
    _ex("Pierna A", 4, "Extensión cuádriceps", 3, "12-15", "piernas"),
    _ex("Pierna A", 5, "Hip thrust barra", 3, "10-12", "piernas", pos=True),
    _ex("Pierna A", 6, "Elevación de gemelos", 4, "15", "piernas"),
    _ex("Torso B", 1, "Press inclinado mancuernas", 4, "10-12", "pecho"),
    _ex("Torso B", 2, "Dominadas lastre", 3, "6-8", "espalda"),
    _ex("Torso B", 3, "Dips en paralelas", 3, "10-12", "pecho"),
    _ex("Torso B", 4, "Remo en polea baja agarre neutro", 3, "10-12", "espalda"),
    _ex("Torso B", 5, "Face pull en polea", 3, "15", "hombros", pos=True),
    _ex("Pierna B", 1, "Peso muerto", 4, "4-6", "espalda"),
    _ex("Pierna B", 2, "Sentadilla búlgara", 3, "8-10", "piernas"),
    _ex("Pierna B", 3, "Curl femoral tumbado", 3, "12-15", "piernas"),
    _ex("Pierna B", 4, "Abducción de cadera máquina", 3, "12-15", "piernas", pos=True),
    _ex("Pierna B", 5, "Elevación de gemelos sentado", 4, "15-20", "piernas"),
    _ex("Torso C", 1, "Aperturas con mancuernas", 3, "12-15", "pecho"),
    _ex("Torso C", 2, "Remo con mancuerna unilateral", 3, "10-12", "espalda"),
    _ex("Torso C", 3, "Press hombro mancuernas", 3, "10-12", "hombros"),
    _ex("Torso C", 4, "Curl bíceps", 3, "10-12", "brazos"),
    _ex("Torso C", 5, "Extensión tríceps", 3, "12", "brazos"),
],

"Pérdida de Grasa HIIT 3x": [
    _ex("Día A", 1, "Sentadilla goblet con mancuerna", 3, "15", "piernas"),
    _ex("Día A", 2, "Press con mancuernas banco plano", 3, "12-15", "pecho"),
    _ex("Día A", 3, "Remo con mancuerna unilateral", 3, "12-15", "espalda"),
    _ex("Día A", 4, "Burpees", 3, "10", "cardio"),
    _ex("Día A", 5, "Mountain climbers", 3, "30s", "core"),
    _ex("Día A", 6, "Plancha frontal", 3, "30s", "core", pos=True),
    _ex("Día B", 1, "Peso muerto mancuernas", 3, "12-15", "piernas"),
    _ex("Día B", 2, "Press inclinado mancuernas", 3, "12-15", "pecho"),
    _ex("Día B", 3, "Zancadas alternas", 3, "12/lado", "piernas"),
    _ex("Día B", 4, "Jumping jacks", 3, "45s", "cardio"),
    _ex("Día B", 5, "Sentadilla con salto", 3, "10", "cardio"),
    _ex("Día C", 1, "Sentadilla sumo mancuerna", 3, "15", "piernas"),
    _ex("Día C", 2, "Press hombro mancuernas de pie", 3, "12-15", "hombros"),
    _ex("Día C", 3, "Remo en polea baja", 3, "12-15", "espalda"),
    _ex("Día C", 4, "Elevaciones de rodillas en suspensión", 3, "12", "core"),
    _ex("Día C", 5, "Bicicleta estática HIIT", 1, "20min", "cardio"),
],

"Pérdida de Grasa Circuito": [
    _ex("Circuito A", 1, "Sentadilla goblet", 3, "15", "piernas"),
    _ex("Circuito A", 2, "Flexiones de pecho", 3, "15", "pecho"),
    _ex("Circuito A", 3, "Remo en TRX o polea", 3, "15", "espalda"),
    _ex("Circuito A", 4, "Zancadas caminar", 3, "12/lado", "piernas"),
    _ex("Circuito A", 5, "Burpees", 3, "10", "cardio"),
    _ex("Circuito A", 6, "Plancha", 3, "30s", "core", pos=True),
    _ex("Circuito B", 1, "Press banca mancuernas", 3, "15", "pecho"),
    _ex("Circuito B", 2, "Jalón polea agarre ancho", 3, "15", "espalda"),
    _ex("Circuito B", 3, "Press hombro de pie", 3, "12-15", "hombros"),
    _ex("Circuito B", 4, "Curl bíceps alternado", 3, "12/lado", "brazos"),
    _ex("Circuito B", 5, "Extensión tríceps sobre cabeza", 3, "12", "brazos"),
    _ex("Circuito B", 6, "Mountain climbers", 3, "30s", "core"),
    _ex("Circuito C", 1, "Peso muerto mancuernas", 3, "15", "piernas"),
    _ex("Circuito C", 2, "Hip thrust cuerpo peso", 3, "20", "piernas", pos=True),
    _ex("Circuito C", 3, "Prensa piernas", 3, "15", "piernas"),
    _ex("Circuito C", 4, "Curl femoral máquina", 3, "15", "piernas"),
    _ex("Circuito C", 5, "Sentadilla con salto", 3, "12", "cardio"),
    _ex("Circuito D", 1, "Bicicleta estática", 1, "10min", "cardio"),
    _ex("Circuito D", 2, "Caminata inclinada", 1, "10min", "cardio"),
    _ex("Circuito D", 3, "Burpees", 4, "10", "cardio"),
    _ex("Circuito D", 4, "Sentadilla saltada", 4, "10", "cardio"),
    _ex("Circuito D", 5, "Plancha", 4, "30s", "core", pos=True),
],

"Cardio + Fuerza 5x": [
    _ex("Día 1 Fuerza", 1, "Sentadilla", 4, "8-10", "piernas"),
    _ex("Día 1 Fuerza", 2, "Press banca", 3, "8-10", "pecho"),
    _ex("Día 1 Fuerza", 3, "Remo barra", 3, "8-10", "espalda"),
    _ex("Día 1 Fuerza", 4, "Bicicleta estática cardio", 1, "20min", "cardio"),
    _ex("Día 2 Cardio", 1, "Trote o bicicleta moderada", 1, "30-40min", "cardio"),
    _ex("Día 2 Cardio", 2, "Plancha", 3, "45s", "core", pos=True),
    _ex("Día 2 Cardio", 3, "Bird-dog", 3, "10/lado", "core", pos=True),
    _ex("Día 3 Fuerza", 1, "Press militar", 4, "8-10", "hombros"),
    _ex("Día 3 Fuerza", 2, "Dominadas o jalón", 4, "8-10", "espalda"),
    _ex("Día 3 Fuerza", 3, "Dips en paralelas", 3, "10-12", "pecho"),
    _ex("Día 3 Fuerza", 4, "Elíptica o remo", 1, "15min", "cardio"),
    _ex("Día 4 Activo", 1, "Estiramientos dinámicos", 1, "10min", "movilidad"),
    _ex("Día 4 Activo", 2, "Foam roller columna", 1, "5min", "movilidad", pos=True),
    _ex("Día 4 Activo", 3, "Caminata moderada", 1, "20min", "cardio"),
    _ex("Día 5 Full", 1, "Sentadilla o prensa", 3, "10-12", "piernas"),
    _ex("Día 5 Full", 2, "Remo mancuerna", 3, "10-12", "espalda"),
    _ex("Día 5 Full", 3, "Press inclinado", 3, "10-12", "pecho"),
    _ex("Día 5 Full", 4, "Hip thrust", 3, "12-15", "piernas", pos=True),
    _ex("Día 5 Full", 5, "Bicicleta HIIT", 1, "20min", "cardio"),
],

"Resistencia Funcional 3x": [
    _ex("Día A", 1, "Sentadilla goblet", 3, "15", "piernas"),
    _ex("Día A", 2, "Flexiones", 3, "15", "pecho"),
    _ex("Día A", 3, "Remo TRX o polea", 3, "15", "espalda"),
    _ex("Día A", 4, "Plancha frontal", 3, "40s", "core", pos=True),
    _ex("Día A", 5, "Puente glúteo", 3, "20", "piernas", pos=True),
    _ex("Día B", 1, "Peso muerto mancuernas", 3, "12", "piernas"),
    _ex("Día B", 2, "Dominadas asistidas", 3, "8-10", "espalda"),
    _ex("Día B", 3, "Zancada con mancuerna", 3, "12/lado", "piernas"),
    _ex("Día B", 4, "Press hombro mancuernas", 3, "12-15", "hombros"),
    _ex("Día B", 5, "Mountain climbers", 3, "30s", "core"),
    _ex("Día C", 1, "Sentadilla búlgara cuerpo peso", 3, "12/lado", "piernas"),
    _ex("Día C", 2, "Remo renegado", 3, "8/lado", "espalda"),
    _ex("Día C", 3, "Press mancuernas una mano", 3, "10/lado", "pecho"),
    _ex("Día C", 4, "Plancha lateral", 3, "30s/lado", "core", pos=True),
    _ex("Día C", 5, "Elevación de talones en escalón", 3, "15", "piernas"),
],

"Resistencia Avanzada 5x": [
    _ex("Día 1", 1, "Sentadilla 20 reps", 5, "20", "piernas"),
    _ex("Día 1", 2, "Press banca superserie con aperturas", 4, "15+15", "pecho"),
    _ex("Día 1", 3, "Remo barra + jalón superserie", 4, "12+12", "espalda"),
    _ex("Día 2", 1, "Peso muerto", 5, "8-10", "espalda"),
    _ex("Día 2", 2, "Sentadilla búlgara", 4, "15/lado", "piernas"),
    _ex("Día 2", 3, "Hip thrust barra", 4, "15-20", "piernas", pos=True),
    _ex("Día 2", 4, "Gemelos pie + sentado superserie", 4, "15+20", "piernas"),
    _ex("Día 3", 1, "Press hombro superserie elevaciones", 4, "12+12", "hombros"),
    _ex("Día 3", 2, "Dominadas + jalón agarre neutro", 4, "10+10", "espalda"),
    _ex("Día 3", 3, "Face pull", 4, "20", "hombros", pos=True),
    _ex("Día 3", 4, "Curl bíceps + martillo superserie", 3, "12+12", "brazos"),
    _ex("Día 4", 1, "Prensa piernas pie bajo alto alternado", 4, "12+12", "piernas"),
    _ex("Día 4", 2, "Extensión + curl superserie", 4, "15+15", "piernas"),
    _ex("Día 4", 3, "Abducción máquina", 4, "20", "piernas", pos=True),
    _ex("Día 5", 1, "Press inclinado + aperturas inclinado", 4, "12+12", "pecho"),
    _ex("Día 5", 2, "Remo mancuerna + jalón superserie", 4, "12+10", "espalda"),
    _ex("Día 5", 3, "Dips + fondos banco superserie", 3, "12+12", "pecho"),
    _ex("Día 5", 4, "Plancha + plancha lateral", 3, "45s+30s", "core", pos=True),
],

"Movilidad & Flexibilidad": [
    _ex("Día A", 1, "Apertura de pecho en marco de puerta", 2, "30s", "movilidad", pos=True),
    _ex("Día A", 2, "Cat-cow columna", 2, "10 reps", "movilidad", pos=True),
    _ex("Día A", 3, "Rotación torácica en suelo", 2, "8/lado", "movilidad", pos=True),
    _ex("Día A", 4, "Estiramiento flexores de cadera", 2, "45s/lado", "movilidad"),
    _ex("Día A", 5, "Apertura de cadera mariposa", 2, "60s", "movilidad"),
    _ex("Día A", 6, "Estiramiento isquiotibiales tumbado", 2, "45s/lado", "movilidad"),
    _ex("Día B", 1, "Pigeon pose modificado", 2, "60s/lado", "movilidad"),
    _ex("Día B", 2, "World's greatest stretch", 2, "6/lado", "movilidad"),
    _ex("Día B", 3, "Estiramiento de lat en polea", 2, "30s/lado", "movilidad", pos=True),
    _ex("Día B", 4, "Figure 4 glúteo tumbado", 2, "60s/lado", "movilidad"),
    _ex("Día B", 5, "Círculos de cuello", 2, "8/lado", "movilidad", pos=True),
    _ex("Día C", 1, "Foam roller columna torácica", 2, "2min", "movilidad", pos=True),
    _ex("Día C", 2, "Extensión torácica en rodillo", 2, "5 reps/zona", "movilidad", pos=True),
    _ex("Día C", 3, "Torsión espinal sentado", 2, "45s/lado", "movilidad", pos=True),
    _ex("Día C", 4, "Child's pose", 2, "60s", "movilidad"),
    _ex("Día C", 5, "Apertura de hombros con banda", 2, "15 reps", "movilidad", pos=True),
],

"Movilidad Avanzada 5x": [
    _ex("Día 1", 1, "Calentamiento dinámico articular", 1, "10min", "movilidad"),
    _ex("Día 1", 2, "Squat profundo con pausa", 3, "10×3s", "movilidad"),
    _ex("Día 1", 3, "Jefferson curl (peso ligero)", 3, "6-8", "movilidad", pos=True),
    _ex("Día 1", 4, "Pigeon pose activo", 3, "60s/lado", "movilidad"),
    _ex("Día 2", 1, "Shoulder CARs", 3, "5/lado", "movilidad", pos=True),
    _ex("Día 2", 2, "Rotación torácica en suelo", 3, "10/lado", "movilidad", pos=True),
    _ex("Día 2", 3, "Open books", 3, "10/lado", "movilidad", pos=True),
    _ex("Día 2", 4, "Wall slides", 3, "10-12", "movilidad", pos=True),
    _ex("Día 3", 1, "Hip CARs", 3, "5/lado", "movilidad"),
    _ex("Día 3", 2, "Sentadilla overhead", 3, "8", "movilidad"),
    _ex("Día 3", 3, "Zancada con rotación torácica", 3, "6/lado", "movilidad"),
    _ex("Día 3", 4, "Estiramiento psoas profundo", 3, "60s/lado", "movilidad"),
    _ex("Día 4", 1, "Extensión torácica en rodillo", 3, "10/zona", "movilidad", pos=True),
    _ex("Día 4", 2, "Cat-cow activo", 3, "10 reps", "movilidad", pos=True),
    _ex("Día 4", 3, "Neck CARs", 2, "5/lado", "movilidad", pos=True),
    _ex("Día 4", 4, "Foam roller cuerpo completo", 1, "10min", "movilidad"),
    _ex("Día 5", 1, "Flujo de yoga fuerza", 1, "20min", "movilidad"),
    _ex("Día 5", 2, "Parada de manos asistida", 3, "30s", "hombros", pos=True),
    _ex("Día 5", 3, "L-sit en paralelas", 3, "10-15s", "core"),
    _ex("Día 5", 4, "Relajación y respiración", 1, "5min", "movilidad"),
],

"Rehabilitación Tobillo": [
    _ex("Día A", 1, "Eversión con banda elástica sentado", 3, "15-20", "rehabilitacion", ank=True),
    _ex("Día A", 2, "Inversión con banda elástica sentado", 3, "15", "rehabilitacion", ank=True),
    _ex("Día A", 3, "Excéntrico de pantorrilla en escalón", 3, "15", "rehabilitacion", ank=True),
    _ex("Día A", 4, "Movilidad tobillo knee-to-wall", 2, "10/lado", "rehabilitacion", ank=True),
    _ex("Día A", 5, "Equilibrio monopodal", 3, "30s/lado", "rehabilitacion", ank=True),
    _ex("Día A", 6, "Prensa de piernas (carga baja)", 3, "15", "piernas"),
    _ex("Día B", 1, "Extensión cuádriceps máquina", 3, "15", "piernas"),
    _ex("Día B", 2, "Hip thrust peso corporal", 3, "20", "piernas", pos=True),
    _ex("Día B", 3, "Abducción de cadera máquina", 3, "15", "piernas", pos=True),
    _ex("Día B", 4, "Face pull en polea", 3, "15", "hombros", pos=True),
    _ex("Día B", 5, "Plancha", 3, "30s", "core", pos=True),
    _ex("Día C", 1, "Eversión con banda elástica", 3, "20", "rehabilitacion", ank=True),
    _ex("Día C", 2, "Excéntrico de pantorrilla", 3, "15", "rehabilitacion", ank=True),
    _ex("Día C", 3, "Estiramiento de sóleo rodilla flexionada", 3, "45s/lado", "rehabilitacion", ank=True),
    _ex("Día C", 4, "Sentadilla en máquina Smith (ROM reducido)", 3, "12", "piernas"),
    _ex("Día C", 5, "Curl femoral máquina", 3, "12-15", "piernas"),
    _ex("Día D", 1, "Caminata controlada 15min", 1, "15min", "cardio"),
    _ex("Día D", 2, "Bicicleta estática sin resistencia", 1, "15min", "cardio"),
    _ex("Día D", 3, "Eversión banda", 3, "20", "rehabilitacion", ank=True),
    _ex("Día D", 4, "Movilidad tobillo activo", 2, "10/lado", "rehabilitacion", ank=True),
    _ex("Día D", 5, "Estiramiento pantorrilla pared", 3, "45s/lado", "rehabilitacion", ank=True),
],

"Rehabilitación Rodilla": [
    _ex("Día A", 1, "Extensión cuádriceps 0-30°", 3, "15", "rehabilitacion"),
    _ex("Día A", 2, "Terminal knee extension (TKE) banda", 3, "15", "rehabilitacion"),
    _ex("Día A", 3, "Hip thrust peso corporal", 3, "20", "piernas", pos=True),
    _ex("Día A", 4, "Abducción de cadera tumbado banda", 3, "15-20", "piernas", pos=True),
    _ex("Día A", 5, "Monster walk con banda", 3, "20 pasos", "piernas"),
    _ex("Día A", 6, "Sentadilla en caja (ROM reducido)", 3, "10-12", "piernas"),
    _ex("Día B", 1, "Prensa piernas ángulo seguro", 3, "12-15", "piernas"),
    _ex("Día B", 2, "Curl femoral tumbado", 3, "12-15", "piernas"),
    _ex("Día B", 3, "Puente glúteo unilateral", 3, "12/lado", "piernas", pos=True),
    _ex("Día B", 4, "Plancha frontal", 3, "30-45s", "core", pos=True),
    _ex("Día B", 5, "Bird-dog", 3, "10/lado", "core", pos=True),
    _ex("Día C", 1, "Bicicleta estática (resistencia baja)", 1, "20min", "cardio"),
    _ex("Día C", 2, "Hip thrust barra (progresivo)", 3, "12", "piernas", pos=True),
    _ex("Día C", 3, "Terminal knee extension", 3, "15", "rehabilitacion"),
    _ex("Día C", 4, "Estiramiento cuádriceps de pie", 2, "45s/lado", "movilidad"),
    _ex("Día C", 5, "Estiramiento isquiotibiales tumbado", 2, "45s/lado", "movilidad"),
],

"Rehabilitación Hombro": [
    _ex("Día A", 1, "Rotación externa con banda sentado", 3, "15", "rehabilitacion", pos=True),
    _ex("Día A", 2, "Rotación interna con banda", 3, "15", "rehabilitacion", pos=True),
    _ex("Día A", 3, "Face pull en polea (cuerda)", 3, "15-20", "rehabilitacion", pos=True),
    _ex("Día A", 4, "Y-T-W en banco inclinado", 3, "10/forma", "rehabilitacion", pos=True),
    _ex("Día A", 5, "Wall slides", 3, "12", "movilidad", pos=True),
    _ex("Día B", 1, "Jalón al pecho agarre ancho", 3, "12-15", "espalda"),
    _ex("Día B", 2, "Remo en polea baja agarre neutro", 3, "12-15", "espalda"),
    _ex("Día B", 3, "Rotación externa banda en pie", 3, "15", "rehabilitacion", pos=True),
    _ex("Día B", 4, "Press mancuernas banco inclinado 30°", 3, "12", "pecho"),
    _ex("Día B", 5, "Curl bíceps mancuernas", 3, "12", "brazos"),
    _ex("Día C", 1, "Pendulum (rotación pasiva)", 2, "1min/lado", "rehabilitacion", pos=True),
    _ex("Día C", 2, "Rotación externa mancuerna tumbado", 3, "12-15", "rehabilitacion", pos=True),
    _ex("Día C", 3, "Serratus wall push", 3, "12-15", "rehabilitacion", pos=True),
    _ex("Día C", 4, "Remo con mancuerna (codo pegado)", 3, "12/lado", "espalda"),
    _ex("Día C", 5, "Trapecio inferior Y en banco inclinado", 3, "12", "hombros", pos=True),
],

"Salud General 3x/sem": [
    _ex("Día A", 1, "Sentadilla con mancuernas", 3, "12-15", "piernas"),
    _ex("Día A", 2, "Press banca mancuernas", 3, "12-15", "pecho"),
    _ex("Día A", 3, "Remo con mancuerna", 3, "12-15", "espalda"),
    _ex("Día A", 4, "Plancha", 3, "30s", "core", pos=True),
    _ex("Día A", 5, "Bicicleta estática", 1, "15min", "cardio"),
    _ex("Día B", 1, "Peso muerto mancuernas", 3, "10-12", "piernas"),
    _ex("Día B", 2, "Jalón al pecho", 3, "10-12", "espalda"),
    _ex("Día B", 3, "Press hombro mancuernas", 3, "10-12", "hombros"),
    _ex("Día B", 4, "Hip thrust peso corporal", 3, "15-20", "piernas", pos=True),
    _ex("Día B", 5, "Elíptica suave", 1, "15min", "cardio"),
    _ex("Día C", 1, "Prensa piernas", 3, "12-15", "piernas"),
    _ex("Día C", 2, "Remo en polea baja", 3, "12-15", "espalda"),
    _ex("Día C", 3, "Curl bíceps + extensión tríceps", 3, "12", "brazos"),
    _ex("Día C", 4, "Elevaciones laterales", 3, "12-15", "hombros"),
    _ex("Día C", 5, "Caminata moderada", 1, "20min", "cardio"),
],

"Salud General 4x/sem": [
    _ex("Día A", 1, "Sentadilla", 3, "10-12", "piernas"),
    _ex("Día A", 2, "Press banca", 3, "10-12", "pecho"),
    _ex("Día A", 3, "Remo con barra", 3, "10-12", "espalda"),
    _ex("Día A", 4, "Plancha", 3, "30-45s", "core", pos=True),
    _ex("Día A", 5, "Bicicleta 15min", 1, "15min", "cardio"),
    _ex("Día B", 1, "Prensa piernas", 3, "12-15", "piernas"),
    _ex("Día B", 2, "Jalón al pecho", 3, "10-12", "espalda"),
    _ex("Día B", 3, "Press hombro", 3, "10-12", "hombros"),
    _ex("Día B", 4, "Hip thrust", 3, "12-15", "piernas", pos=True),
    _ex("Día B", 5, "Elíptica 15min", 1, "15min", "cardio"),
    _ex("Día C", 1, "Peso muerto rumano", 3, "10-12", "piernas"),
    _ex("Día C", 2, "Press inclinado mancuernas", 3, "10-12", "pecho"),
    _ex("Día C", 3, "Dominadas asistidas o jalón", 3, "8-10", "espalda"),
    _ex("Día C", 4, "Bird-dog", 3, "10/lado", "core", pos=True),
    _ex("Día C", 5, "Caminata 20min", 1, "20min", "cardio"),
    _ex("Día D", 1, "Curl bíceps + tríceps cuerda", 3, "12", "brazos"),
    _ex("Día D", 2, "Elevaciones laterales", 3, "12-15", "hombros"),
    _ex("Día D", 3, "Abducción cadera máquina", 3, "15", "piernas", pos=True),
    _ex("Día D", 4, "Face pull", 3, "15", "hombros", pos=True),
    _ex("Día D", 5, "Yoga suave o movilidad", 1, "15min", "movilidad"),
],

"Salud General Avanzada": [
    _ex("Día 1", 1, "Sentadilla", 4, "8-10", "piernas"),
    _ex("Día 1", 2, "Press banca", 4, "8-10", "pecho"),
    _ex("Día 1", 3, "Remo barra Pendlay", 4, "6-8", "espalda"),
    _ex("Día 1", 4, "Face pull", 3, "15", "hombros", pos=True),
    _ex("Día 1", 5, "Cardio HIIT bicicleta", 1, "20min", "cardio"),
    _ex("Día 2", 1, "Peso muerto", 4, "5-6", "espalda"),
    _ex("Día 2", 2, "Sentadilla búlgara", 3, "10/lado", "piernas"),
    _ex("Día 2", 3, "Hip thrust barra", 3, "12-15", "piernas", pos=True),
    _ex("Día 2", 4, "Plancha + variaciones", 3, "45s", "core", pos=True),
    _ex("Día 3", 1, "Press militar", 4, "8-10", "hombros"),
    _ex("Día 3", 2, "Dominadas lastre", 4, "6-8", "espalda"),
    _ex("Día 3", 3, "Dips lastre", 3, "8-10", "pecho"),
    _ex("Día 3", 4, "Elevaciones laterales", 3, "12-15", "hombros"),
    _ex("Día 4", 1, "Prensa piernas volumen", 4, "12-15", "piernas"),
    _ex("Día 4", 2, "Curl femoral", 4, "12-15", "piernas"),
    _ex("Día 4", 3, "Extensión cuádriceps", 3, "15", "piernas"),
    _ex("Día 4", 4, "Gemelos pie + sentado", 4, "15+15", "piernas"),
    _ex("Día 5", 1, "Press inclinado", 3, "10-12", "pecho"),
    _ex("Día 5", 2, "Remo polea neutro", 3, "10-12", "espalda"),
    _ex("Día 5", 3, "Curl + tríceps superserie", 3, "12+12", "brazos"),
    _ex("Día 5", 4, "Cardio moderado", 1, "30min", "cardio"),
],

"Rutina 1 — Base salud": [
    _ex("Lunes Empuje", 1, "Face pull en polea (cuerda)", 3, "15-20", "hombros", pos=True),
    _ex("Lunes Empuje", 2, "Press de banca plana (barra)", 4, "10-12", "pecho"),
    _ex("Lunes Empuje", 3, "Press inclinado con mancuernas", 3, "10-12", "pecho"),
    _ex("Lunes Empuje", 4, "Press militar en máquina", 3, "10-12", "hombros"),
    _ex("Lunes Empuje", 5, "Elevaciones laterales", 3, "12-15", "hombros"),
    _ex("Lunes Empuje", 6, "Extensión de tríceps en polea cuerda", 3, "12-15", "brazos"),
    _ex("Martes Jale", 1, "Jalón al pecho agarre ancho", 4, "10-12", "espalda"),
    _ex("Martes Jale", 2, "Remo en polea baja un brazo", 3, "10-12", "espalda"),
    _ex("Martes Jale", 3, "Remo en máquina sentado agarre neutro", 3, "10-12", "espalda"),
    _ex("Martes Jale", 4, "Jalón agarre supino", 3, "10-12", "espalda", pos=True),
    _ex("Martes Jale", 5, "Curl en polea baja con barra", 3, "10-12", "brazos"),
    _ex("Martes Jale", 6, "Curl en polea baja con cuerda martillo", 3, "12", "brazos"),
    _ex("Miércoles Activo", 1, "Foam rolling columna torácica", 2, "2min", "movilidad", pos=True),
    _ex("Miércoles Activo", 2, "Extensión torácica sobre rodillo", 2, "5/zona", "movilidad", pos=True),
    _ex("Miércoles Activo", 3, "Estiramiento cadena posterior", 2, "2min/lado", "movilidad"),
    _ex("Miércoles Activo", 4, "Movilidad cadera paloma modificada", 2, "90s/lado", "movilidad"),
    _ex("Miércoles Activo", 5, "Cat-cow + rotación torácica", 2, "10 reps", "movilidad", pos=True),
    _ex("Jueves Piernas", 1, "Prensa de piernas máquina", 4, "12-15", "piernas"),
    _ex("Jueves Piernas", 2, "Extensión cuádriceps máquina", 3, "12-15", "piernas"),
    _ex("Jueves Piernas", 3, "Curl femoral tumbado máquina", 3, "12-15", "piernas"),
    _ex("Jueves Piernas", 4, "Hip thrust", 4, "12-15", "piernas", pos=True),
    _ex("Jueves Piernas", 5, "Abducción en máquina", 3, "15-20", "piernas", pos=True),
    _ex("Jueves Piernas", 6, "Eversión con banda elástica sentado", 3, "15-20", "rehabilitacion", ank=True),
    _ex("Jueves Piernas", 7, "Excéntrico de pantorrilla en escalón", 3, "15", "rehabilitacion", ank=True),
    _ex("Viernes Core", 1, "Plancha frontal", 3, "30-45s", "core", pos=True),
    _ex("Viernes Core", 2, "Plancha lateral", 3, "20-30s/lado", "core", pos=True),
    _ex("Viernes Core", 3, "Crunch en máquina", 3, "15-20", "core"),
    _ex("Viernes Core", 4, "Superman en suelo", 3, "12-15", "core", pos=True),
    _ex("Viernes Core", 5, "Bird-dog", 3, "10/lado", "core", pos=True),
    _ex("Viernes Core", 6, "Pallof press polea", 3, "12/lado", "core"),
    _ex("Sábado Full", 1, "Remo en máquina sentado", 3, "12", "espalda"),
    _ex("Sábado Full", 2, "Press de mancuernas banco plano", 3, "12", "pecho"),
    _ex("Sábado Full", 3, "Prensa de piernas peso ligero", 3, "15", "piernas"),
    _ex("Sábado Full", 4, "Y-T-W en banco inclinado", 3, "10/forma", "hombros", pos=True),
    _ex("Sábado Full", 5, "Curl mancuernas excéntrico", 3, "12", "brazos"),
    _ex("Sábado Full", 6, "Eversión con banda elástica", 3, "15-20", "rehabilitacion", ank=True),
    _ex("Sábado Full", 7, "Excéntrico de pantorrilla en escalón", 3, "15", "rehabilitacion", ank=True),
],

"Fuerza Avanzada 6x": [
    _ex("Empuje A", 1, "Press banca plana pesado", 5, "3-5", "pecho"),
    _ex("Empuje A", 2, "Press inclinado barra", 4, "5-6", "pecho"),
    _ex("Empuje A", 3, "Press hombro barra", 4, "5-6", "hombros"),
    _ex("Empuje A", 4, "Dips lastre", 3, "6-8", "pecho"),
    _ex("Empuje A", 5, "Extensión tríceps cuerda", 3, "10-12", "brazos"),
    _ex("Jale A", 1, "Dominadas lastre", 5, "4-6", "espalda"),
    _ex("Jale A", 2, "Remo barra pesado", 4, "5-6", "espalda"),
    _ex("Jale A", 3, "Remo Pendlay", 4, "4-5", "espalda"),
    _ex("Jale A", 4, "Face pull", 3, "15", "hombros", pos=True),
    _ex("Jale A", 5, "Curl bíceps barra", 3, "8-10", "brazos"),
    _ex("Piernas A", 1, "Sentadilla", 5, "3-5", "piernas"),
    _ex("Piernas A", 2, "Peso muerto rumano", 4, "5-6", "piernas"),
    _ex("Piernas A", 3, "Prensa piernas", 4, "8-10", "piernas"),
    _ex("Piernas A", 4, "Curl femoral", 3, "8-10", "piernas"),
    _ex("Empuje B", 1, "Press hombro mancuernas", 4, "6-8", "hombros"),
    _ex("Empuje B", 2, "Press inclinado mancuernas", 4, "8-10", "pecho"),
    _ex("Empuje B", 3, "Cruce polea aperturas", 3, "12-15", "pecho"),
    _ex("Empuje B", 4, "Elevaciones laterales", 4, "12-15", "hombros"),
    _ex("Jale B", 1, "Jalón agarre ancho", 4, "6-8", "espalda"),
    _ex("Jale B", 2, "Remo mancuerna unilateral", 4, "8-10", "espalda"),
    _ex("Jale B", 3, "Remo cara polea", 3, "15", "hombros", pos=True),
    _ex("Jale B", 4, "Curl predicador", 3, "10-12", "brazos"),
    _ex("Piernas B", 1, "Peso muerto", 5, "3-4", "espalda"),
    _ex("Piernas B", 2, "Sentadilla búlgara", 4, "8/lado", "piernas"),
    _ex("Piernas B", 3, "Hip thrust barra", 4, "10-12", "piernas", pos=True),
    _ex("Piernas B", 4, "Abducción cadera", 3, "15", "piernas", pos=True),
],

"Cuerpo y Mente 4x": [
    _ex("Día 1", 1, "Respiración diafragmática 5min", 1, "5min", "movilidad"),
    _ex("Día 1", 2, "Sentadilla goblet meditativa", 3, "10 lentas", "piernas"),
    _ex("Día 1", 3, "Press banca consciente", 3, "10-12", "pecho"),
    _ex("Día 1", 4, "Remo barra controlado", 3, "10-12", "espalda"),
    _ex("Día 1", 5, "Plancha con respiración", 3, "45s", "core", pos=True),
    _ex("Día 1", 6, "Yoga restaurativo", 1, "10min", "movilidad"),
    _ex("Día 2", 1, "Flujo de movilidad matinal", 1, "10min", "movilidad"),
    _ex("Día 2", 2, "Hip thrust controlado", 3, "12-15", "piernas", pos=True),
    _ex("Día 2", 3, "Jalón al pecho mente-músculo", 3, "12", "espalda"),
    _ex("Día 2", 4, "Face pull consciente", 3, "15", "hombros", pos=True),
    _ex("Día 2", 5, "Caminata meditativa", 1, "20min", "cardio"),
    _ex("Día 3", 1, "Respiración + movilidad", 1, "10min", "movilidad"),
    _ex("Día 3", 2, "Press hombro lento", 3, "10-12", "hombros"),
    _ex("Día 3", 3, "Dominadas controladas", 3, "6-8", "espalda"),
    _ex("Día 3", 4, "Curl bíceps isométrico 2s", 3, "10", "brazos"),
    _ex("Día 3", 5, "Estiramiento profundo 10min", 1, "10min", "movilidad"),
    _ex("Día 4", 1, "Yoga fuerza 20min", 1, "20min", "movilidad"),
    _ex("Día 4", 2, "Sentadilla búlgara lenta", 3, "10/lado", "piernas"),
    _ex("Día 4", 3, "Peso muerto rumano consciente", 3, "10", "piernas"),
    _ex("Día 4", 4, "Plancha lateral respiración", 3, "30s/lado", "core", pos=True),
    _ex("Día 4", 5, "Meditación post-entrenamiento", 1, "5min", "movilidad"),
],

"Atlético Explosivo 4x": [
    _ex("Día 1 Pliometría", 1, "Saltos a cajón (box jump)", 4, "5", "piernas"),
    _ex("Día 1 Pliometría", 2, "Saltos con sentadilla", 3, "8", "piernas"),
    _ex("Día 1 Pliometría", 3, "Sprint 30m", 6, "1", "cardio"),
    _ex("Día 1 Pliometría", 4, "Sentadilla explosiva (barra)", 4, "4-5", "piernas"),
    _ex("Día 1 Pliometría", 5, "Hip thrust explosivo", 3, "8", "piernas", pos=True),
    _ex("Día 2 Fuerza", 1, "Press banca", 4, "5-6", "pecho"),
    _ex("Día 2 Fuerza", 2, "Remo barra", 4, "5-6", "espalda"),
    _ex("Día 2 Fuerza", 3, "Press hombro", 3, "6-8", "hombros"),
    _ex("Día 2 Fuerza", 4, "Dominadas lastradas", 3, "5-6", "espalda"),
    _ex("Día 2 Fuerza", 5, "Plancha", 3, "45s", "core", pos=True),
    _ex("Día 3 Velocidad", 1, "Sprint corto 10m × 10", 10, "1", "cardio"),
    _ex("Día 3 Velocidad", 2, "Saltos laterales", 4, "8/lado", "piernas"),
    _ex("Día 3 Velocidad", 3, "Peso muerto", 4, "4-5", "espalda"),
    _ex("Día 3 Velocidad", 4, "Zancada explosiva", 3, "8/lado", "piernas"),
    _ex("Día 4 Potencia", 1, "Clean & press (mancuernas)", 4, "5", "hombros"),
    _ex("Día 4 Potencia", 2, "Sentadilla frontal", 4, "5", "piernas"),
    _ex("Día 4 Potencia", 3, "Burpees con salto", 4, "10", "cardio"),
    _ex("Día 4 Potencia", 4, "Saltos cuerda o skipping", 3, "1min", "cardio"),
    _ex("Día 4 Potencia", 5, "Core anti-rotación Pallof", 3, "12/lado", "core"),
],

"Mantenimiento 3x": [
    _ex("Día A", 1, "Sentadilla", 3, "8-10", "piernas"),
    _ex("Día A", 2, "Press banca", 3, "8-10", "pecho"),
    _ex("Día A", 3, "Remo barra", 3, "8-10", "espalda"),
    _ex("Día A", 4, "Press hombro", 2, "10-12", "hombros"),
    _ex("Día A", 5, "Plancha", 2, "30s", "core", pos=True),
    _ex("Día B", 1, "Peso muerto", 3, "5-6", "espalda"),
    _ex("Día B", 2, "Jalón al pecho", 3, "10-12", "espalda"),
    _ex("Día B", 3, "Prensa piernas", 3, "10-12", "piernas"),
    _ex("Día B", 4, "Elevaciones laterales", 2, "12-15", "hombros"),
    _ex("Día B", 5, "Face pull", 2, "15", "hombros", pos=True),
    _ex("Día C", 1, "Sentadilla búlgara", 3, "10/lado", "piernas"),
    _ex("Día C", 2, "Press inclinado mancuernas", 3, "10-12", "pecho"),
    _ex("Día C", 3, "Dominadas o jalón", 3, "8-10", "espalda"),
    _ex("Día C", 4, "Curl bíceps + tríceps cuerda", 2, "12", "brazos"),
    _ex("Día C", 5, "Bicicleta o elíptica 15min", 1, "15min", "cardio"),
],

}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date(d: str) -> str:
    if not _DATE_RE.match(d):
        raise ValueError(f"Formato de fecha inválido: {d!r}")
    return d


@st.cache_resource
def get_client() -> Client:
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


# ── auth ──────────────────────────────────────────────────────────────────────

def sign_up(email: str, password: str):
    return get_client().auth.sign_up({"email": email, "password": password})


def sign_in(email: str, password: str):
    return get_client().auth.sign_in_with_password({"email": email, "password": password})


def sign_out():
    get_client().auth.sign_out()


def get_or_create_profile(user_id: str, display_name: str = "") -> dict:
    c = get_client()
    res = c.table("profiles").select("*").eq("auth_user_id", user_id).execute()
    if res.data:
        return res.data[0]
    return c.table("profiles").insert({
        "auth_user_id": user_id,
        "name": display_name or "Entrenador",
    }).execute().data[0]


# ── No-ops (tables managed in Supabase dashboard) ─────────────────────────────

def init_db():
    pass


def migrate_db():
    pass


# ── Seed achievements ─────────────────────────────────────────────────────────

def seed_achievements():
    c = get_client()
    res = c.table("achievements").select("id", count="exact").execute()
    if (res.count or 0) > 0:
        return
    _ACHIEVEMENTS = [
        ("primera_sesion",      "🏁 Primera sesión",           "Completa tu primera sesión",                        "🏁", 50,   "consistencia", "sessions_total",     1),
        ("semana_1",            "🔥 Una semana activo",         "Completa 7 sesiones en total",                      "🔥", 100,  "consistencia", "sessions_total",     7),
        ("mes_1",               "📅 Un mes en el gym",          "Acumula 30 sesiones completadas",                   "📅", 300,  "consistencia", "sessions_total",     30),
        ("tres_meses",          "💪 Tres meses",                "90 sesiones — ya es un hábito real",                "💪", 750,  "consistencia", "sessions_total",     90),
        ("seis_meses",          "🏆 Seis meses",                "180 sesiones. Constancia total.",                   "🏆", 1500, "consistencia", "sessions_total",     180),
        ("un_año",              "👑 Un año",                    "365 sesiones. Leyenda viva.",                       "👑", 3000, "consistencia", "sessions_total",     365),
        ("racha_7",             "🔥×7 Racha de 7 días",         "7 días consecutivos",                               "⚡", 150,  "consistencia", "streak_days",        7),
        ("racha_14",            "⚡ Racha de 14 días",          "14 días sin parar",                                 "⚡", 300,  "consistencia", "streak_days",        14),
        ("racha_30",            "🌟 Racha de 30 días",          "Un mes completo de racha",                          "🌟", 600,  "consistencia", "streak_days",        30),
        ("semana_perfecta",     "✨ Semana perfecta",           "Cumple todas las metas semanales",                  "✨", 200,  "consistencia", "perfect_weeks",      1),
        ("ejercicios_50",       "💥 50 ejercicios",             "Completa 50 ejercicios en total",                   "💥", 100,  "volumen",      "exercises_total",    50),
        ("ejercicios_100",      "🎯 100 ejercicios",            "100 ejercicios completados",                        "🎯", 200,  "volumen",      "exercises_total",    100),
        ("ejercicios_250",      "🏋️ 250 ejercicios",           "250 ejercicios — el volumen suma",                  "🏋️",400,  "volumen",      "exercises_total",    250),
        ("ejercicios_500",      "🔱 500 ejercicios",            "500 ejercicios. Máquina de trabajo.",               "🔱", 750,  "volumen",      "exercises_total",    500),
        ("ejercicios_1000",     "🌌 1000 ejercicios",           "1000 ejercicios completados. Élite.",               "🌌", 1500, "volumen",      "exercises_total",    1000),
        ("postura_7",           "🧘 7 días de postura",         "Completa la rutina de postura 7 días",              "🧘", 100,  "volumen",      "posture_days",       7),
        ("postura_30",          "🌿 30 días de postura",        "30 días de postura completados",                    "🌿", 400,  "volumen",      "posture_days",       30),
        ("madrugador",          "🌅 Madrugador",                "10 sesiones registradas",                           "🌅", 200,  "volumen",      "sessions_total",     10),
        ("nocturno",            "🌙 Búho nocturno",             "10 sesiones completadas",                           "🌙", 200,  "volumen",      "sessions_total",     10),
        ("fin_de_semana",       "🏖️ Guerrero de fin de semana", "10 sesiones",                                      "🏖️",150,  "volumen",      "sessions_total",     10),
        ("primera_rutina",      "📋 Primera rutina",            "Activa tu primera rutina",                          "📋", 100,  "rutinas",      "routines_completed", 1),
        ("rutinas_3",           "📚 3 rutinas",                 "Completa 3 rutinas distintas",                      "📚", 250,  "rutinas",      "routines_completed", 3),
        ("rutinas_5",           "🎓 5 rutinas",                 "5 rutinas completadas",                             "🎓", 500,  "rutinas",      "routines_completed", 5),
        ("rutinas_10",          "🏛️ 10 rutinas",               "10 rutinas. Diversidad total.",                     "🏛️",1000, "rutinas",      "routines_completed", 10),
        ("rutinas_25",          "🌠 ¡Las 25 rutinas!",          "Completaste las 25 plantillas. Leyenda.",            "🌠", 5000, "rutinas",      "routines_completed", 25),
        ("fuerza_iniciado",     "⚔️ Iniciado en Fuerza",       "Completa una rutina de fuerza",                     "⚔️", 200, "rutinas",      "routines_completed", 1),
        ("hipertrofia_iniciado","💪 Iniciado en Hipertrofia",   "Completa una rutina de hipertrofia",                "💪", 200, "rutinas",      "routines_completed", 1),
        ("cardio_iniciado",     "🏃 Iniciado en Cardio",        "Completa una rutina de pérdida de grasa",           "🏃", 200, "rutinas",      "routines_completed", 1),
        ("movilidad_iniciado",  "🧘 Iniciado en Movilidad",     "Completa una rutina de movilidad",                  "🧘", 200, "rutinas",      "routines_completed", 1),
        ("explorador",          "🗺️ Explorador",               "Prueba 5 categorías de rutinas distintas",          "🗺️",300, "rutinas",      "routines_completed", 5),
        ("nivel_2",   "⭐ Nivel 2",           "Alcanza el nivel 2",   "⭐", 0, "niveles", "level_reached", 2),
        ("nivel_5",   "⭐⭐ Nivel 5",         "Alcanza el nivel 5",   "⭐", 0, "niveles", "level_reached", 5),
        ("nivel_10",  "🌟 Nivel 10",          "Alcanza el nivel 10",  "🌟", 0, "niveles", "level_reached", 10),
        ("nivel_15",  "💫 Nivel 15",          "Alcanza el nivel 15",  "💫", 0, "niveles", "level_reached", 15),
        ("nivel_20",  "✨ Nivel 20",          "Alcanza el nivel 20",  "✨", 0, "niveles", "level_reached", 20),
        ("nivel_25",  "🏆 Nivel 25",          "Alcanza el nivel 25",  "🏆", 0, "niveles", "level_reached", 25),
        ("nivel_30",  "👑 Nivel 30",          "Alcanza el nivel 30",  "👑", 0, "niveles", "level_reached", 30),
        ("nivel_40",  "🔱 Nivel 40",          "Alcanza el nivel 40",  "🔱", 0, "niveles", "level_reached", 40),
        ("nivel_50",  "🌌 Nivel 50",          "Alcanza el nivel 50",  "🌌", 0, "niveles", "level_reached", 50),
        ("nivel_100", "🌠 Leyenda Nivel 100", "Nivel máximo alcanzado","🌠", 0, "niveles", "level_reached", 100),
    ]
    rows = [
        {
            "code": code, "name": name, "description": desc, "icon": icon,
            "xp_reward": xp, "category": cat,
            "condition_type": ctype, "condition_value": cval,
        }
        for code, name, desc, icon, xp, cat, ctype, cval in _ACHIEVEMENTS
    ]
    c.table("achievements").insert(rows).execute()


# ── Seed routine templates ────────────────────────────────────────────────────

def seed_routine_templates():
    c = get_client()
    res = c.table("routine_templates").select("id", count="exact").execute()
    if (res.count or 0) > 0:
        return

    templates = [
        {"name": "Fuerza Base 3x/sem",        "description": "Sentadilla, peso muerto y press. Progresión lineal.", "goal": "fuerza",        "level": "principiante", "days_per_week": 3, "duration_weeks": 8},
        {"name": "Fuerza Intermedia 4x/sem",   "description": "Upper/Lower split. Periodización ondulante.",         "goal": "fuerza",        "level": "intermedio",   "days_per_week": 4, "duration_weeks": 8},
        {"name": "Powerlifting 5x/sem",        "description": "Especialización en los 3 grandes levantamientos.",    "goal": "fuerza",        "level": "avanzado",     "days_per_week": 5, "duration_weeks": 12},
        {"name": "Hipertrofia Push/Pull/Legs", "description": "PPL clásico. 6 días, máximo volumen muscular.",        "goal": "hipertrofia",   "level": "intermedio",   "days_per_week": 6, "duration_weeks": 10},
        {"name": "Hipertrofia Full Body 3x",   "description": "Full body con énfasis en hipertrofia. Ideal para principiantes.", "goal": "hipertrofia", "level": "principiante", "days_per_week": 3, "duration_weeks": 8},
        {"name": "Hipertrofia Upper/Lower",    "description": "4 días upper/lower con volumen progresivo.",           "goal": "hipertrofia",   "level": "intermedio",   "days_per_week": 4, "duration_weeks": 10},
        {"name": "Hipertrofia Torso/Pierna",   "description": "Split torso/pierna con alta frecuencia.",              "goal": "hipertrofia",   "level": "avanzado",     "days_per_week": 5, "duration_weeks": 10},
        {"name": "Pérdida de Grasa HIIT 3x",   "description": "HIIT + pesas. Máximo gasto calórico.",                "goal": "perdida_grasa", "level": "principiante", "days_per_week": 3, "duration_weeks": 8},
        {"name": "Pérdida de Grasa Circuito",  "description": "Circuitos metabólicos de alta intensidad.",           "goal": "perdida_grasa", "level": "intermedio",   "days_per_week": 4, "duration_weeks": 8},
        {"name": "Cardio + Fuerza 5x",         "description": "Combinación de cardio moderado y fuerza.",            "goal": "perdida_grasa", "level": "intermedio",   "days_per_week": 5, "duration_weeks": 10},
        {"name": "Resistencia Funcional 3x",   "description": "Entrenamiento funcional de alta resistencia.",        "goal": "resistencia",   "level": "principiante", "days_per_week": 3, "duration_weeks": 8},
        {"name": "Resistencia Avanzada 5x",    "description": "Volumen alto, series largas, poca recuperación.",     "goal": "resistencia",   "level": "avanzado",     "days_per_week": 5, "duration_weeks": 10},
        {"name": "Movilidad & Flexibilidad",   "description": "Yoga-gym. Fuerza + rango de movimiento.",             "goal": "movilidad",     "level": "principiante", "days_per_week": 3, "duration_weeks": 6},
        {"name": "Movilidad Avanzada 5x",      "description": "Trabajo de movilidad articular profunda.",            "goal": "movilidad",     "level": "avanzado",     "days_per_week": 5, "duration_weeks": 8},
        {"name": "Rehabilitación Tobillo",     "description": "Programa peroneal + equilibrio. Adaptado para tobillo.", "goal": "rehabilitacion", "level": "principiante", "days_per_week": 4, "duration_weeks": 8},
        {"name": "Rehabilitación Rodilla",     "description": "Fortalecimiento gradual VMO y glúteos.",              "goal": "rehabilitacion", "level": "principiante", "days_per_week": 3, "duration_weeks": 10},
        {"name": "Rehabilitación Hombro",      "description": "Trabajo de manguito rotador y estabilizadores.",      "goal": "rehabilitacion", "level": "principiante", "days_per_week": 3, "duration_weeks": 8},
        {"name": "Salud General 3x/sem",       "description": "Rutina completa para mantenerse en forma.",           "goal": "salud_general", "level": "principiante", "days_per_week": 3, "duration_weeks": 8},
        {"name": "Salud General 4x/sem",       "description": "Equilibrio entre fuerza, cardio y flexibilidad.",     "goal": "salud_general", "level": "principiante", "days_per_week": 4, "duration_weeks": 8},
        {"name": "Salud General Avanzada",     "description": "Alto volumen con variedad. Cuerpo completo.",         "goal": "salud_general", "level": "avanzado",     "days_per_week": 5, "duration_weeks": 10},
        {"name": "Rutina 1 — Base salud",      "description": "Plan inicial de retorno al gym. Tobillo/peroneal adaptado.", "goal": "salud_general", "level": "principiante", "days_per_week": 6, "duration_weeks": 8},
        {"name": "Fuerza Avanzada 6x",         "description": "Alta frecuencia por grupos musculares. Para avanzados.", "goal": "fuerza",    "level": "avanzado",     "days_per_week": 6, "duration_weeks": 12},
        {"name": "Cuerpo y Mente 4x",          "description": "Integra meditación activa, respiración y fuerza.",    "goal": "salud_general", "level": "intermedio",   "days_per_week": 4, "duration_weeks": 8},
        {"name": "Atlético Explosivo 4x",      "description": "Pliometría, sprints y fuerza explosiva.",             "goal": "resistencia",   "level": "avanzado",     "days_per_week": 4, "duration_weeks": 8},
        {"name": "Mantenimiento 3x",           "description": "Mantener condición física actual sin sobrecarga.",    "goal": "salud_general", "level": "intermedio",   "days_per_week": 3, "duration_weeks": 4},
    ]
    res2 = c.table("routine_templates").insert(templates).execute()
    # add a few exercises for the first template so the UI has something
    if res2.data:
        tid = res2.data[0]["id"]
        exs = [
            {"template_id": tid, "day_name": "Día A", "order_index": 1, "exercise_name": "Sentadilla", "sets": "3", "reps": "8-10", "category": "piernas", "is_posture": False, "is_ankle": False},
            {"template_id": tid, "day_name": "Día A", "order_index": 2, "exercise_name": "Press banca", "sets": "3", "reps": "8-10", "category": "pecho",  "is_posture": False, "is_ankle": False},
            {"template_id": tid, "day_name": "Día B", "order_index": 1, "exercise_name": "Peso muerto", "sets": "3", "reps": "5",    "category": "espalda","is_posture": False, "is_ankle": False},
            {"template_id": tid, "day_name": "Día B", "order_index": 2, "exercise_name": "Remo con barra", "sets": "3", "reps": "8", "category": "espalda","is_posture": False, "is_ankle": False},
        ]
        c.table("template_exercises").insert(exs).execute()


# ── Seed template exercises (idempotent per-template) ─────────────────────────

def seed_template_exercises():
    """Seed exercise programs for any template that currently has 0 exercises."""
    c = get_client()
    templates_res = c.table("routine_templates").select("id,name").execute()
    if not templates_res.data:
        return

    # Get set of template IDs that already have exercises
    ex_res = c.table("template_exercises").select("template_id").execute()
    seeded_ids: set[int] = {r["template_id"] for r in (ex_res.data or [])}

    for tmpl in templates_res.data:
        tid  = tmpl["id"]
        name = tmpl["name"]
        if tid in seeded_ids:
            continue
        exs = _TMPL_EXERCISES.get(name)
        if not exs:
            continue
        rows = [{**ex, "template_id": tid} for ex in exs]
        try:
            c.table("template_exercises").insert(rows).execute()
        except Exception:
            pass


# ── user_xp ───────────────────────────────────────────────────────────────────

def init_user_xp(profile_id: int = 1):
    c = get_client()
    res = c.table("user_xp").select("id").eq("profile_id", profile_id).execute()
    if not res.data:
        c.table("user_xp").insert({
            "profile_id": profile_id,
            "total_xp": 0, "current_level": 1,
            "current_streak": 0, "longest_streak": 0,
            "total_sessions": 0, "total_exercises_completed": 0,
        }).execute()


def get_user_xp(profile_id: int = 1) -> dict | None:
    res = get_client().table("user_xp").select("*").eq("profile_id", profile_id).execute()
    return dict(res.data[0]) if res.data else None


def update_user_xp(profile_id: int, **kwargs):
    allowed = {
        "total_xp", "current_level", "current_streak", "longest_streak",
        "last_session_date", "total_sessions", "total_exercises_completed",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    get_client().table("user_xp").update(fields).eq("profile_id", profile_id).execute()


def add_xp_log(profile_id: int, event_type: str, xp_gained: int, description: str = ""):
    get_client().table("xp_log").insert({
        "profile_id": profile_id,
        "event_type": event_type,
        "xp_gained":  xp_gained,
        "description": description,
    }).execute()


def get_xp_log(profile_id: int, limit: int = 20) -> list[dict]:
    res = (
        get_client().table("xp_log")
        .select("*")
        .eq("profile_id", profile_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def xp_log_exists_today(profile_id: int, event_type: str, description: str) -> bool:
    from datetime import date
    today = date.today().isoformat()
    res = (
        get_client().table("xp_log")
        .select("id")
        .eq("profile_id", profile_id)
        .eq("event_type", event_type)
        .eq("description", description)
        .gte("created_at", today)
        .execute()
    )
    return bool(res.data)


# ── achievements ──────────────────────────────────────────────────────────────

def get_all_achievements() -> list[dict]:
    res = get_client().table("achievements").select("*").order("category").execute()
    return res.data or []


def get_user_achievements(profile_id: int) -> list[dict]:
    res = (
        get_client().table("user_achievements")
        .select("*, achievements(*)")
        .eq("profile_id", profile_id)
        .execute()
    )
    # flatten: merge achievements fields into top-level dict
    out = []
    for row in (res.data or []):
        ach = dict(row.get("achievements") or {})
        flat = {k: v for k, v in row.items() if k != "achievements"}
        out.append({**ach, **flat})
    return out


def unlock_achievement(profile_id: int, achievement_id: int) -> bool:
    try:
        get_client().table("user_achievements").insert({
            "profile_id": profile_id,
            "achievement_id": achievement_id,
        }).execute()
        return True
    except Exception:
        return False


# ── sessions ──────────────────────────────────────────────────────────────────

def get_session(date: str, profile_id: int = 1) -> bool:
    _validate_date(date)
    res = (
        get_client().table("sessions")
        .select("completed")
        .eq("profile_id", profile_id)
        .eq("date", date)
        .execute()
    )
    return bool(res.data[0]["completed"]) if res.data else False


def toggle_session(date: str, profile_id: int = 1):
    _validate_date(date)
    current = get_session(date, profile_id)
    get_client().table("sessions").upsert(
        {"profile_id": profile_id, "date": date, "completed": not current},
        on_conflict="profile_id,date",
    ).execute()


# ── exercises ─────────────────────────────────────────────────────────────────

def set_exercise(date: str, exercise_id: str, completed: bool, profile_id: int = 1):
    _validate_date(date)
    row_id = f"{profile_id}:{date}:{exercise_id}"
    get_client().table("exercises").upsert(
        {"id": row_id, "profile_id": profile_id, "date": date,
         "exercise_id": exercise_id, "completed": completed},
        on_conflict="id",
    ).execute()


def get_exercises_for_date(date: str, profile_id: int = 1) -> dict:
    _validate_date(date)
    res = (
        get_client().table("exercises")
        .select("exercise_id,completed")
        .eq("profile_id", profile_id)
        .eq("date", date)
        .execute()
    )
    return {r["exercise_id"]: bool(r["completed"]) for r in (res.data or [])}


# ── posture ───────────────────────────────────────────────────────────────────

def set_posture(date: str, exercise_id: str, completed: bool, profile_id: int = 1):
    _validate_date(date)
    row_id = f"{profile_id}:{date}:{exercise_id}"
    get_client().table("posture").upsert(
        {"id": row_id, "profile_id": profile_id, "date": date,
         "exercise_id": exercise_id, "completed": completed},
        on_conflict="id",
    ).execute()


def get_posture_for_date(date: str, profile_id: int = 1) -> dict:
    _validate_date(date)
    res = (
        get_client().table("posture")
        .select("exercise_id,completed")
        .eq("profile_id", profile_id)
        .eq("date", date)
        .execute()
    )
    return {r["exercise_id"]: bool(r["completed"]) for r in (res.data or [])}


# ── stats ─────────────────────────────────────────────────────────────────────

def get_stats_for_dates(dates: list[str], profile_id: int = 1) -> dict:
    if not dates:
        return {"sessions": {}, "exercises": [], "posture": []}
    c = get_client()
    sess_res = (
        c.table("sessions")
        .select("date,completed")
        .eq("profile_id", profile_id)
        .in_("date", dates)
        .execute()
    )
    ex_res = (
        c.table("exercises")
        .select("date,exercise_id,completed")
        .eq("profile_id", profile_id)
        .in_("date", dates)
        .execute()
    )
    pos_res = (
        c.table("posture")
        .select("date,exercise_id,completed")
        .eq("profile_id", profile_id)
        .in_("date", dates)
        .execute()
    )
    return {
        "sessions":  {r["date"]: bool(r["completed"]) for r in (sess_res.data or [])},
        "exercises": [dict(r) for r in (ex_res.data  or [])],
        "posture":   [dict(r) for r in (pos_res.data or [])],
    }


# ── routines ──────────────────────────────────────────────────────────────────

def get_all_routines(profile_id: int = 1) -> list[dict]:
    res = (
        get_client().table("routines")
        .select("*")
        .eq("profile_id", profile_id)
        .order("id")
        .execute()
    )
    return res.data or []


def add_routine(version: str, name: str, start_date: str, notes: str, profile_id: int = 1):
    c = get_client()
    # close any open routine
    open_res = (
        c.table("routines")
        .select("id")
        .eq("profile_id", profile_id)
        .is_("end_date", "null")
        .execute()
    )
    for r in (open_res.data or []):
        c.table("routines").update({"end_date": start_date}).eq("id", r["id"]).execute()
    c.table("routines").insert({
        "profile_id": profile_id, "version": version,
        "name": name, "start_date": start_date, "notes": notes,
    }).execute()


def get_active_routine(profile_id: int = 1) -> dict | None:
    res = (
        get_client().table("routines")
        .select("*")
        .eq("profile_id", profile_id)
        .is_("end_date", "null")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def get_routines_by_profile(profile_id: int = 1) -> list[dict]:
    res = (
        get_client().table("routines")
        .select("*")
        .eq("profile_id", profile_id)
        .order("id")
        .execute()
    )
    return res.data or []


def create_routine(profile_id: int, version: str, name: str, start_date: str, notes: str):
    c = get_client()
    open_res = (
        c.table("routines")
        .select("id")
        .eq("profile_id", profile_id)
        .is_("end_date", "null")
        .execute()
    )
    for r in (open_res.data or []):
        c.table("routines").update({"end_date": start_date}).eq("id", r["id"]).execute()
    c.table("routines").insert({
        "profile_id": profile_id, "version": version,
        "name": name, "start_date": start_date, "notes": notes,
    }).execute()


def get_routine_days(routine_id: int) -> list[dict]:
    res = (
        get_client().table("routine_days")
        .select("*")
        .eq("routine_id", routine_id)
        .order("order_index")
        .execute()
    )
    return res.data or []


def get_exercises_for_routine_day(routine_id: int, day_name: str) -> list[dict]:
    routine_res = get_client().table("routines").select("version").eq("id", routine_id).execute()
    if not routine_res.data:
        return []
    version = routine_res.data[0]["version"] or ""
    if not version.startswith("tmpl-"):
        return []
    template_id = int(version.split("-")[1])
    res = (
        get_client().table("template_exercises")
        .select("*")
        .eq("template_id", template_id)
        .eq("day_name", day_name)
        .order("order_index")
        .execute()
    )
    return res.data or []


def set_routine_days(routine_id: int, days: list[dict]):
    c = get_client()
    c.table("routine_days").delete().eq("routine_id", routine_id).execute()
    if days:
        rows = [{**d, "routine_id": routine_id} for d in days]
        c.table("routine_days").insert(rows).execute()


# ── profiles ──────────────────────────────────────────────────────────────────

def get_profile(profile_id: int = 1) -> dict | None:
    res = get_client().table("profiles").select("*").eq("id", profile_id).execute()
    return res.data[0] if res.data else None


# ── weekly_goals ──────────────────────────────────────────────────────────────

def get_weekly_goals(profile_id: int, week_start: str) -> dict | None:
    res = (
        get_client().table("weekly_goals")
        .select("*")
        .eq("profile_id", profile_id)
        .eq("week_start", week_start)
        .execute()
    )
    return res.data[0] if res.data else None


def upsert_weekly_goals(profile_id: int, week_start: str, **kwargs):
    allowed = {
        "sessions_goal", "exercises_goal", "posture_days_goal",
        "sessions_done", "exercises_done", "posture_days_done", "completed",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    get_client().table("weekly_goals").upsert(
        {"profile_id": profile_id, "week_start": week_start, **fields},
        on_conflict="profile_id,week_start",
    ).execute()


# ── personal_records ──────────────────────────────────────────────────────────

def get_personal_records(profile_id: int) -> list[dict]:
    res = (
        get_client().table("personal_records")
        .select("*")
        .eq("profile_id", profile_id)
        .order("exercise_name")
        .execute()
    )
    return res.data or []


def upsert_personal_record(
    profile_id: int,
    exercise_name: str,
    record_type: str,
    value: float,
    date: str,
    notes: str = "",
) -> bool:
    c = get_client()
    existing = (
        c.table("personal_records")
        .select("value")
        .eq("profile_id", profile_id)
        .eq("exercise_name", exercise_name)
        .eq("record_type", record_type)
        .execute()
    )
    is_new = not existing.data or value > existing.data[0]["value"]
    c.table("personal_records").upsert(
        {
            "profile_id": profile_id, "exercise_name": exercise_name,
            "record_type": record_type, "value": value, "date": date, "notes": notes,
        },
        on_conflict="profile_id,exercise_name,record_type",
    ).execute()
    return is_new


# ── routine_templates ─────────────────────────────────────────────────────────

def get_all_templates(
    goal: str | None = None,
    level: str | None = None,
    days_per_week: int | None = None,
) -> list[dict]:
    q = get_client().table("routine_templates").select("*")
    if goal:          q = q.eq("goal", goal)
    if level:         q = q.eq("level", level)
    if days_per_week: q = q.eq("days_per_week", days_per_week)
    return q.order("goal").order("name").execute().data or []


def get_template_exercises(template_id: int) -> list[dict]:
    res = (
        get_client().table("template_exercises")
        .select("*")
        .eq("template_id", template_id)
        .order("day_name")
        .order("order_index")
        .execute()
    )
    return res.data or []


# ── perfect-weeks & posture-days counters (for gamification) ──────────────────

def count_perfect_weeks(profile_id: int) -> int:
    res = (
        get_client().table("weekly_goals")
        .select("id", count="exact")
        .eq("profile_id", profile_id)
        .eq("completed", True)
        .execute()
    )
    return res.count or 0


def count_posture_days(profile_id: int) -> int:
    """Days where every posture exercise was completed."""
    from data import POSTURE_ROUTINE
    n = len(POSTURE_ROUTINE)
    res = (
        get_client().table("posture")
        .select("date,completed")
        .eq("profile_id", profile_id)
        .eq("completed", True)
        .execute()
    )
    by_date: dict[str, int] = {}
    for r in (res.data or []):
        by_date[r["date"]] = by_date.get(r["date"], 0) + 1
    return sum(1 for cnt in by_date.values() if cnt >= n)
