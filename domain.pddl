(define (domain warehouse)
 (:requirements :strips :typing)
 (:types robot package location)

 (:predicates
  (at-robot ?r - robot ?l - location)
  (at-package ?p - package ?l - location)
  (carrying ?r - robot ?p - package)
  (robot-free ?r - robot)
  (connected ?from - location ?to - location)
 )

 ;; --- Move action (robot moves between connected zones)
 (:action move
  :parameters (?r - robot ?from - location ?to - location)
  :precondition (and
    (at-robot ?r ?from)
    (connected ?from ?to)
  )
  :effect (and
    (not (at-robot ?r ?from))
    (at-robot ?r ?to)
  )
 )

 ;; --- Pickup action
 (:action pickup
  :parameters (?r - robot ?p - package ?l - location)
  :precondition (and
    (at-robot ?r ?l)
    (at-package ?p ?l)
    (robot-free ?r)
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
  )
  :effect (and
    (at-package ?p ?l)
    (not (carrying ?r ?p))
    (robot-free ?r)
  )
 )
)
