(define (domain warehouse)
 (:requirements :strips :typing)
 (:types robot package location)

 (:predicates
  (at-robot ?r - robot ?l - location)
  (at-package ?p - package ?l - location)
  ;; occupied indicates a location currently occupied by a robot.
  ;; This predicate is used to prevent two robots from occupying the
  ;; same cell simultaneously. Planners should treat (occupied L)
  ;; as a mutual-exclusion resource for robot movement.
  (occupied ?l - location)
  (carrying ?r - robot ?p - package)
  (robot-free ?r - robot)
    (assigned ?p - package ?r - robot)
  (connected ?from - location ?to - location)
 )



;; --- Move action (robot moves between connected zones)
 (:action move
  :parameters (?r - robot ?from - location ?to - location)
  :precondition (and
    (at-robot ?r ?from)
    (connected ?from ?to)
    ;; cannot move into an occupied location
    (not (occupied ?to))
  )
  :effect (and
    (not (at-robot ?r ?from))
    ;; update occupied status: from becomes free, to becomes occupied
    (not (occupied ?from))
    (at-robot ?r ?to)
    (occupied ?to)
  )
 )

 ;; --- Pickup action
 (:action pickup
  :parameters (?r - robot ?p - package ?l - location)
  :precondition (and
    (at-robot ?r ?l)
    (at-package ?p ?l)
    (robot-free ?r)
    (assigned ?p ?r)
     ;; pickup should happen at an occupied location (by the robot performing
     ;; the pickup). This makes the intent explicit to planners and keeps the
     ;; occupied predicate aligned with the robot's position.
     (occupied ?l)
  )
  :effect (and
    (not (at-package ?p ?l))
    (not (robot-free ?r))
    (carrying ?r ?p)
  )
 )

 ;; --- Drop action
 (:action drop
  :parameters (?r - robot ?p - package ?l - location)
  :precondition (and
    (at-robot ?r ?l)
    (carrying ?r ?p)
     ;; dropping occurs at the robot's current (occupied) location; after
     ;; dropping the cell remains occupied by the robot (we don't clear
     ;; occupied here because the robot is still present). If a drop implies
     ;; the robot leaves the cell, domain actions should explicitly clear
     ;; occupied.
  )
  :effect (and
    (at-package ?p ?l)
    (not (carrying ?r ?p))
    (robot-free ?r)
  )
 )
)
