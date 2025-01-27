import os
import pytest
import re
import platform

import numpy as np
from casadi import DM, vertcat
from bioptim import Solver, SolutionMerge

from bioptim.examples.stochastic_optimal_control.arm_reaching_torque_driven_implicit import ExampleType


@pytest.mark.parametrize("use_sx", [True, False])
def test_arm_reaching_muscle_driven(use_sx):
    from bioptim.examples.stochastic_optimal_control import arm_reaching_muscle_driven as ocp_module

    final_time = 0.8
    n_shooting = 4
    hand_final_position = np.array([9.359873986980460e-12, 0.527332023564034])
    example_type = ExampleType.CIRCLE
    force_field_magnitude = 0

    dt = 0.01
    motor_noise_std = 0.05
    wPq_std = 3e-4
    wPqdot_std = 0.0024
    motor_noise_magnitude = DM(np.array([motor_noise_std**2 / dt, motor_noise_std**2 / dt]))
    wPq_magnitude = DM(np.array([wPq_std**2 / dt, wPq_std**2 / dt]))
    wPqdot_magnitude = DM(np.array([wPqdot_std**2 / dt, wPqdot_std**2 / dt]))
    sensory_noise_magnitude = vertcat(wPq_magnitude, wPqdot_magnitude)

    if use_sx:
        if platform.system() == "Windows":
            # It is not possible to test the error message on Windows as it uses absolute path
            match = None
        else:
            match = re.escape(
                "Error in Function::call for 'tp' [MXFunction] at .../casadi/core/function.cpp:339:\n"
                ".../casadi/core/linsol_internal.cpp:65: eval_sx not defined for LinsolQr"
            )
        with pytest.raises(RuntimeError, match=match):
            ocp = ocp_module.prepare_socp(
                final_time=final_time,
                n_shooting=n_shooting,
                hand_final_position=hand_final_position,
                motor_noise_magnitude=motor_noise_magnitude,
                sensory_noise_magnitude=sensory_noise_magnitude,
                force_field_magnitude=force_field_magnitude,
                example_type=example_type,
                use_sx=use_sx,
            )
        return

    ocp = ocp_module.prepare_socp(
        final_time=final_time,
        n_shooting=n_shooting,
        hand_final_position=hand_final_position,
        motor_noise_magnitude=motor_noise_magnitude,
        sensory_noise_magnitude=sensory_noise_magnitude,
        force_field_magnitude=force_field_magnitude,
        example_type=example_type,
        use_sx=use_sx,
    )

    # ocp.print(to_console=True, to_graph=False)  #TODO: check to adjust the print method

    # Solver parameters
    solver = Solver.IPOPT(show_online_optim=False)
    solver.set_maximum_iterations(4)
    solver.set_nlp_scaling_method("none")

    sol = ocp.solve(solver)

    # Check objective function value
    f = np.array(sol.cost)
    np.testing.assert_equal(f.shape, (1, 1))
    np.testing.assert_almost_equal(f[0, 0], 13.32287163458417)

    # detailed cost values
    np.testing.assert_almost_equal(sol.detailed_cost[0]["cost_value_weighted"], 0.6783119392800087)
    np.testing.assert_almost_equal(sol.detailed_cost[1]["cost_value_weighted"], 0.4573562887022004)
    np.testing.assert_almost_equal(
        f[0, 0], sum(sol.detailed_cost[i]["cost_value_weighted"] for i in range(len(sol.detailed_cost)))
    )

    # Check constraints
    g = np.array(sol.constraints)
    np.testing.assert_equal(g.shape, (546, 1))

    # Check some of the results
    states = sol.decision_states(to_merge=SolutionMerge.NODES)
    controls = sol.decision_controls(to_merge=SolutionMerge.NODES)
    algebraic_states = sol.decision_algebraic_states(to_merge=SolutionMerge.NODES)

    q, qdot, mus_activations = states["q"], states["qdot"], states["muscles"]
    mus_excitations = controls["muscles"]
    k, ref, m = algebraic_states["k"], algebraic_states["ref"], algebraic_states["m"]
    # cov = integrated_values["cov"]

    # initial and final position
    np.testing.assert_almost_equal(q[:, 0], np.array([0.34906585, 2.24586773]))
    np.testing.assert_almost_equal(q[:, -1], np.array([0.95993109, 1.15939485]))
    np.testing.assert_almost_equal(qdot[:, 0], np.array((0, 0)))
    np.testing.assert_almost_equal(qdot[:, -1], np.array((0, 0)))
    np.testing.assert_almost_equal(
        mus_activations[:, 0], np.array([0.00559921, 0.00096835, 0.00175969, 0.01424529, 0.01341463, 0.00648656])
    )
    np.testing.assert_almost_equal(
        mus_activations[:, -1], np.array([0.04856166, 0.09609582, 0.02063621, 0.0315381, 0.00022286, 0.0165601])
    )

    np.testing.assert_almost_equal(
        mus_excitations[:, 0], np.array([0.05453449, 0.07515539, 0.02860859, 0.01667135, 0.00352633, 0.04392939])
    )
    np.testing.assert_almost_equal(
        mus_excitations[:, -2], np.array([0.05083793, 0.09576169, 0.02139706, 0.02832909, 0.00023962, 0.02396517])
    )

    np.testing.assert_almost_equal(
        k[:, 0],
        np.array(
            [
                0.00999995,
                0.01,
                0.00999999,
                0.00999998,
                0.00999997,
                0.00999999,
                0.00999994,
                0.01,
                0.01,
                0.00999998,
                0.00999997,
                0.00999999,
                0.0099997,
                0.0099995,
                0.00999953,
                0.00999958,
                0.0099996,
                0.00999953,
                0.0099997,
                0.0099995,
                0.00999953,
                0.00999958,
                0.0099996,
                0.00999953,
            ]
        ),
    )
    np.testing.assert_almost_equal(ref[:, 0], np.array([0.00834655, 0.05367618, 0.00834655, 0.00834655]))
    np.testing.assert_almost_equal(
        m[:, 0],
        np.array(
            [
                1.70810520e-01,
                9.24608816e-03,
                -2.72650658e-02,
                1.05398530e-02,
                8.98374479e-03,
                8.86397629e-03,
                9.77792061e-03,
                8.40556268e-03,
                9.06928287e-03,
                8.39077342e-03,
                3.56453950e-03,
                1.56534006e-01,
                4.74437345e-02,
                -7.63108417e-02,
                8.00827704e-04,
                -2.73081620e-03,
                -3.57625997e-03,
                -5.06587091e-04,
                -1.11586453e-03,
                -1.48700041e-03,
                1.48227603e-02,
                7.90121132e-03,
                7.65728294e-02,
                7.35733915e-03,
                7.53514379e-03,
                7.93071078e-03,
                4.94841001e-03,
                9.42249163e-03,
                7.25722813e-03,
                9.47333066e-03,
                8.57938092e-03,
                1.14023696e-02,
                1.50545445e-02,
                4.32844317e-02,
                5.98000313e-03,
                8.57055714e-03,
                7.38539951e-03,
                7.95998211e-03,
                7.09660591e-03,
                8.64491341e-03,
                -2.74736661e-02,
                8.63061567e-02,
                -1.97257907e-01,
                9.40540321e-01,
                4.23095866e-02,
                1.07457907e-02,
                -4.36284627e-03,
                -1.41585209e-02,
                -2.52062529e-02,
                4.03005838e-03,
                2.29699855e-02,
                -2.95050053e-02,
                1.01220545e-01,
                -4.23529363e-01,
                3.64376975e-02,
                1.04603417e-01,
                1.23306909e-02,
                1.68244003e-02,
                2.18948538e-02,
                8.47777890e-03,
                9.34744296e-02,
                -1.34736043e-02,
                8.27850768e-01,
                -2.41629571e-01,
                1.97804811e-02,
                6.45608415e-03,
                7.64073642e-02,
                2.95987301e-02,
                8.37855333e-03,
                2.53974474e-02,
                -4.05561279e-02,
                2.05592350e-02,
                -4.60172967e-01,
                1.50980662e-01,
                1.55818997e-03,
                9.16055220e-03,
                2.58451398e-02,
                9.51675252e-02,
                8.06247374e-03,
                -1.64248894e-03,
                1.03747046e-02,
                3.18864595e-02,
                6.85657953e-02,
                2.83683345e-01,
                -1.10621504e-02,
                9.55375664e-03,
                -1.19784814e-04,
                4.83155620e-03,
                9.69920902e-02,
                1.02776900e-02,
                -2.69456243e-02,
                -1.24806854e-02,
                -3.64739879e-01,
                -2.20090489e-01,
                2.49629057e-02,
                6.06502722e-03,
                2.79657076e-02,
                3.01937740e-03,
                1.89391527e-02,
                9.74841774e-02,
            ]
        ),
    )


@pytest.mark.parametrize("use_sx", [True, False])
def test_arm_reaching_torque_driven_explicit(use_sx):
    from bioptim.examples.stochastic_optimal_control import arm_reaching_torque_driven_explicit as ocp_module

    final_time = 0.8
    n_shooting = 4
    hand_final_position = np.array([9.359873986980460e-12, 0.527332023564034])

    dt = 0.01
    motor_noise_std = 0.05
    wPq_std = 3e-4
    wPqdot_std = 0.0024
    motor_noise_magnitude = DM(np.array([motor_noise_std**2 / dt, motor_noise_std**2 / dt]))
    wPq_magnitude = DM(np.array([wPq_std**2 / dt, wPq_std**2 / dt]))
    wPqdot_magnitude = DM(np.array([wPqdot_std**2 / dt, wPqdot_std**2 / dt]))
    sensory_noise_magnitude = vertcat(wPq_magnitude, wPqdot_magnitude)

    bioptim_folder = os.path.dirname(ocp_module.__file__)

    if use_sx:
        if platform.system() == "Windows":
            # It is not possible to test the error message on Windows as it uses absolute path
            match = None
        else:
            match = re.escape(
                "Error in Function::call for 'tp' [MXFunction] at .../casadi/core/function.cpp:339:\n"
                ".../casadi/core/linsol_internal.cpp:65: eval_sx not defined for LinsolQr"
            )
        with pytest.raises(RuntimeError, match=match):
            ocp = ocp_module.prepare_socp(
                biorbd_model_path=bioptim_folder + "/models/LeuvenArmModel.bioMod",
                final_time=final_time,
                n_shooting=n_shooting,
                hand_final_position=hand_final_position,
                motor_noise_magnitude=motor_noise_magnitude,
                sensory_noise_magnitude=sensory_noise_magnitude,
                use_sx=use_sx,
            )
        return

    ocp = ocp_module.prepare_socp(
        biorbd_model_path=bioptim_folder + "/models/LeuvenArmModel.bioMod",
        final_time=final_time,
        n_shooting=n_shooting,
        hand_final_position=hand_final_position,
        motor_noise_magnitude=motor_noise_magnitude,
        sensory_noise_magnitude=sensory_noise_magnitude,
        use_sx=use_sx,
    )

    # Solver parameters
    solver = Solver.IPOPT(show_online_optim=False)
    solver.set_maximum_iterations(4)
    solver.set_nlp_scaling_method("none")

    sol = ocp.solve(solver)

    # Check objective function value
    f = np.array(sol.cost)
    np.testing.assert_equal(f.shape, (1, 1))
    np.testing.assert_almost_equal(f[0, 0], 46.99030175091475)

    # detailed cost values
    np.testing.assert_almost_equal(sol.detailed_cost[0]["cost_value_weighted"], 0.055578630313992475)
    np.testing.assert_almost_equal(sol.detailed_cost[1]["cost_value_weighted"], 6.038226210163837)
    np.testing.assert_almost_equal(
        f[0, 0], sum(sol.detailed_cost[i]["cost_value_weighted"] for i in range(len(sol.detailed_cost)))
    )

    # Check constraints
    g = np.array(sol.constraints)
    np.testing.assert_equal(g.shape, (214, 1))

    # Check some of the results
    states = sol.decision_states(to_merge=SolutionMerge.NODES)
    controls = sol.decision_controls(to_merge=SolutionMerge.NODES)
    algebraic_states = sol.decision_algebraic_states(to_merge=SolutionMerge.NODES)

    q, qdot, qddot = states["q"], states["qdot"], states["qddot"]
    qdddot, tau = controls["qdddot"], controls["tau"]
    k, ref, m = algebraic_states["k"], algebraic_states["ref"], algebraic_states["m"]
    ocp.nlp[0].integrated_values["cov"].cx

    # TODO Integrated value is not a proper way to go, it should be removed and recomputed at will
    # cov = integrated_values["cov"]

    # initial and final position
    np.testing.assert_almost_equal(q[:, 0], np.array([0.34906585, 2.24586773]))
    np.testing.assert_almost_equal(q[:, -1], np.array([0.92702265, 1.27828413]))
    np.testing.assert_almost_equal(qdot[:, 0], np.array([0, 0]))
    np.testing.assert_almost_equal(qdot[:, -1], np.array([0, 0]))
    np.testing.assert_almost_equal(qddot[:, 0], np.array([0, 0]))
    np.testing.assert_almost_equal(qddot[:, -1], np.array([0, 0]))

    np.testing.assert_almost_equal(qdddot[:, 0], np.array([0.00124365, 0.00124365]))
    np.testing.assert_almost_equal(qdddot[:, -2], np.array([0.00124365, 0.00124365]))

    np.testing.assert_almost_equal(tau[:, 0], np.array([0.36186712, -0.2368119]))
    np.testing.assert_almost_equal(tau[:, -2], np.array([-0.35709778, 0.18867995]))

    np.testing.assert_almost_equal(
        k[:, 0],
        np.array(
            [
                0.13824554,
                0.54172046,
                0.05570321,
                0.25169273,
                0.00095407,
                0.00121309,
                0.00095146,
                0.00121091,
            ]
        ),
    )
    np.testing.assert_almost_equal(ref[:, 0], np.array([0.02592847, 0.25028511, 0.00124365, 0.00124365]))
    np.testing.assert_almost_equal(
        m[:, 0],
        np.array(
            [
                8.36639386e-01,
                1.14636589e-01,
                -4.32594485e-01,
                1.10372277e00,
                4.73812392e-03,
                4.73812392e-03,
                8.01515210e-02,
                9.66785674e-01,
                7.40822199e-01,
                8.50818498e-01,
                6.74366790e-03,
                6.74366790e-03,
                7.92700393e-02,
                -8.94683551e-03,
                7.86796476e-01,
                -9.53722725e-02,
                6.55990825e-04,
                6.55990825e-04,
                -8.94995258e-04,
                7.69438075e-02,
                -2.33336654e-02,
                7.55054362e-01,
                1.59819032e-03,
                1.59819032e-03,
                1.24365477e-03,
                1.24365477e-03,
                1.24365477e-03,
                1.24365477e-03,
                8.76878178e-01,
                1.24365477e-03,
                1.24365477e-03,
                1.24365477e-03,
                1.24365477e-03,
                1.24365477e-03,
                1.24365477e-03,
                8.76878178e-01,
            ]
        ),
    )


@pytest.mark.parametrize("with_cholesky", [True, False])
@pytest.mark.parametrize("with_scaling", [True, False])
@pytest.mark.parametrize("use_sx", [True, False])
def test_arm_reaching_torque_driven_implicit(with_cholesky, with_scaling, use_sx):
    from bioptim.examples.stochastic_optimal_control import arm_reaching_torque_driven_implicit as ocp_module

    if with_cholesky and not with_scaling:
        return
    if not with_cholesky and not with_scaling and not use_sx:
        return
    if with_cholesky and with_scaling and use_sx:
        return
    if with_cholesky and with_scaling and not use_sx:
        return

    final_time = 0.8
    n_shooting = 4
    hand_final_position = np.array([9.359873986980460e-12, 0.527332023564034])

    dt = 0.01
    motor_noise_std = 0.05
    wPq_std = 3e-4
    wPqdot_std = 0.0024
    motor_noise_magnitude = DM(np.array([motor_noise_std**2 / dt, motor_noise_std**2 / dt]))
    wPq_magnitude = DM(np.array([wPq_std**2 / dt, wPq_std**2 / dt]))
    wPqdot_magnitude = DM(np.array([wPqdot_std**2 / dt, wPqdot_std**2 / dt]))
    sensory_noise_magnitude = vertcat(wPq_magnitude, wPqdot_magnitude)

    bioptim_folder = os.path.dirname(ocp_module.__file__)

    ocp = ocp_module.prepare_socp(
        biorbd_model_path=bioptim_folder + "/models/LeuvenArmModel.bioMod",
        final_time=final_time,
        n_shooting=n_shooting,
        hand_final_position=hand_final_position,
        motor_noise_magnitude=motor_noise_magnitude,
        sensory_noise_magnitude=sensory_noise_magnitude,
        with_cholesky=with_cholesky,
        with_scaling=with_scaling,
        use_sx=use_sx,
    )

    # Solver parameters
    solver = Solver.IPOPT(show_online_optim=False)
    solver.set_maximum_iterations(4)
    solver.set_nlp_scaling_method("none")

    sol = ocp.solve(solver)

    # Check objective
    f = np.array(sol.cost)
    np.testing.assert_equal(f.shape, (1, 1))

    # Check constraints values
    g = np.array(sol.constraints)
    np.testing.assert_equal(g.shape, (378, 1))

    # Check some of the solution values
    states = sol.decision_states(to_merge=SolutionMerge.NODES)
    controls = sol.decision_controls(to_merge=SolutionMerge.NODES)
    algebraic_states = sol.decision_algebraic_states(to_merge=SolutionMerge.NODES)

    q, qdot = states["q"], states["qdot"]
    tau = controls["tau"]

    if not with_cholesky:
        # Check some of the results
        k, ref, m, cov, a, c = (
            algebraic_states["k"],
            algebraic_states["ref"],
            algebraic_states["m"],
            algebraic_states["cov"],
            algebraic_states["a"],
            algebraic_states["c"],
        )
        if not with_scaling:
            # Check objective function value
            np.testing.assert_almost_equal(f[0, 0], 62.83236488441526)

            # detailed cost values
            np.testing.assert_almost_equal(sol.detailed_cost[0]["cost_value_weighted"], 62.48137304816964)
            np.testing.assert_almost_equal(sol.detailed_cost[1]["cost_value_weighted"], 0.3509918362456358)
            np.testing.assert_almost_equal(
                f[0, 0], sum(sol.detailed_cost[i]["cost_value_weighted"] for i in range(len(sol.detailed_cost)))
            )

            # initial and final position
            np.testing.assert_almost_equal(q[:, 0], np.array([0.34906585, 2.24586773]))
            np.testing.assert_almost_equal(q[:, -1], np.array([0.9256103, 1.29037205]))
            np.testing.assert_almost_equal(qdot[:, 0], np.array([0, 0]))
            np.testing.assert_almost_equal(qdot[:, -1], np.array([0, 0]))

            np.testing.assert_almost_equal(tau[:, 0], np.array([0.41942813, -0.29886019]))
            np.testing.assert_almost_equal(tau[:, -2], np.array([-0.39449672, 0.36921743]))

            np.testing.assert_almost_equal(
                k[:, 0],
                np.array(
                    [-0.0790218, 0.27128222, 0.15890697, -0.49504993, 0.0463122, -0.3824336, -0.08291488, 0.1947862]
                ),
            )
            np.testing.assert_almost_equal(ref[:, 0], np.array([2.81907786e-02, 2.84412560e-01, 0, 0]))
            np.testing.assert_almost_equal(
                m[:, 0],
                np.array(
                    [
                        1.11119915e00,
                        -1.44056147e-04,
                        -7.92387508e-03,
                        1.29653660e-02,
                        4.03350767e-04,
                        1.11072947e00,
                        -3.63028044e-02,
                        3.43506625e-02,
                        -1.22287288e-02,
                        -4.03446951e-04,
                        1.10058636e00,
                        3.63086964e-02,
                        -5.38166455e-05,
                        -1.21464871e-02,
                        4.84391756e-03,
                        1.09318297e00,
                    ]
                ),
            )

            np.testing.assert_almost_equal(
                cov[:, -2],
                np.array(
                    [
                        -2.44361371e-05,
                        5.03988822e-05,
                        -2.53889736e-04,
                        5.54490654e-04,
                        5.03988822e-05,
                        -1.05730935e-04,
                        4.57675296e-04,
                        -1.03369318e-03,
                        -2.53889736e-04,
                        4.57675296e-04,
                        -4.38051559e-03,
                        9.28976812e-03,
                        5.54490654e-04,
                        -1.03369318e-03,
                        9.28976812e-03,
                        -2.03118675e-02,
                    ]
                ),
            )

            np.testing.assert_almost_equal(
                a[:, 3],
                np.array(
                    [
                        1.00000000e00,
                        2.83470503e-29,
                        -2.73371469e-01,
                        5.61967286e-01,
                        -5.54924440e-28,
                        1.00000000e00,
                        -1.06373905e00,
                        2.76850288e00,
                        -1.00000000e-01,
                        2.69216079e-27,
                        5.97588981e-01,
                        1.05005559e00,
                        -1.54142332e-27,
                        -1.00000000e-01,
                        -1.20328930e-02,
                        9.99955126e-01,
                    ]
                ),
            )

            np.testing.assert_almost_equal(
                c[:, 2],
                np.array(
                    [
                        -4.51226127e-30,
                        8.33773592e-30,
                        -1.35562569e00,
                        1.12573123e00,
                        1.73767029e-29,
                        1.26613716e-28,
                        1.12573123e00,
                        -3.79219059e00,
                        -2.46703922e-29,
                        -2.77757617e-28,
                        8.44560218e-02,
                        -2.14525153e-01,
                        -2.12049507e-28,
                        -7.55987586e-28,
                        7.46209951e-01,
                        -2.20583953e00,
                        -4.98343155e-25,
                        -4.67005692e-27,
                        4.43752625e-01,
                        -7.50216036e-01,
                        -1.13596005e-27,
                        2.87218037e-27,
                        -2.08200045e-01,
                        5.33395037e-01,
                    ]
                ),
            )
    else:
        # Check some of the results
        k, ref, m, cov, a, c = (
            algebraic_states["k"],
            algebraic_states["ref"],
            algebraic_states["m"],
            algebraic_states["cholesky_cov"],
            algebraic_states["a"],
            algebraic_states["c"],
        )
        if not with_scaling:
            # Check objective function value
            np.testing.assert_almost_equal(f[0, 0], 62.40222244200586)

            # detailed cost values
            np.testing.assert_almost_equal(sol.detailed_cost[0]["cost_value_weighted"], 62.40222242539446)
            np.testing.assert_almost_equal(sol.detailed_cost[1]["cost_value_weighted"], 1.6611394850611363e-08)
            np.testing.assert_almost_equal(
                f[0, 0], sum(sol.detailed_cost[i]["cost_value_weighted"] for i in range(len(sol.detailed_cost)))
            )

            # initial and final position
            np.testing.assert_almost_equal(q[:, 0], np.array([0.34906585, 2.24586773]))
            np.testing.assert_almost_equal(q[:, -1], np.array([0.9256103, 1.29037205]))
            np.testing.assert_almost_equal(qdot[:, 0], np.array([0, 0]))
            np.testing.assert_almost_equal(qdot[:, -1], np.array([0, 0]))

            np.testing.assert_almost_equal(tau[:, 0], np.array([0.42135681, -0.30494449]))
            np.testing.assert_almost_equal(tau[:, -2], np.array([-0.39329963, 0.36152636]))

            np.testing.assert_almost_equal(
                k[:, 0],
                np.array(
                    [0.00227125, 0.01943845, -0.00045809, 0.04340353, -0.05890334, -0.02196787, 0.02044042, -0.08280278]
                ),
            )
            np.testing.assert_almost_equal(ref[:, 0], np.array([2.81907786e-02, 2.84412560e-01, 0, 0]))
            np.testing.assert_almost_equal(
                m[:, 0],
                np.array(
                    [
                        1.11111643e00,
                        9.66024409e-06,
                        -4.78746311e-04,
                        -8.69421987e-04,
                        1.49883122e-04,
                        1.11128979e00,
                        -1.34894811e-02,
                        -1.60812429e-02,
                        -1.23773893e-02,
                        -6.07070546e-05,
                        1.11396504e00,
                        5.46363498e-03,
                        -2.04675057e-05,
                        -1.22691010e-02,
                        1.84207561e-03,
                        1.10421909e00,
                    ]
                ),
            )

            np.testing.assert_almost_equal(
                cov[:, -2],
                np.array(
                    [
                        0.00644836,
                        -0.00610657,
                        -0.00544246,
                        0.00168837,
                        0.0005854,
                        -0.00123564,
                        0.0103952,
                        0.01108306,
                        -0.00252879,
                        -0.00192049,
                    ]
                ),
            )

            np.testing.assert_almost_equal(
                a[:, 3],
                np.array(
                    [
                        1.00000000e00,
                        -2.17926087e-13,
                        1.26870284e-03,
                        -3.78607634e-02,
                        -2.56284891e-13,
                        1.00000000e00,
                        -2.19752019e-01,
                        4.81445536e-01,
                        -1.00000000e-01,
                        1.09505432e-13,
                        1.02554762e00,
                        4.87997817e-02,
                        9.63854391e-14,
                        -1.00000000e-01,
                        4.91622255e-02,
                        8.87744034e-01,
                    ]
                ),
            )

            np.testing.assert_almost_equal(
                c[:, 2],
                np.array(
                    [
                        2.24899604e-16,
                        4.19692812e-16,
                        -1.35499970e00,
                        1.12950726e00,
                        -1.16296826e-16,
                        -5.23075855e-16,
                        1.12950726e00,
                        -3.79903118e00,
                        6.93079055e-17,
                        4.43906938e-16,
                        -2.00791886e-02,
                        4.98852395e-02,
                        3.32248534e-16,
                        1.04710774e-15,
                        -4.28795369e-02,
                        9.36788627e-02,
                        -2.55942876e-13,
                        -2.73014494e-13,
                        5.33498922e-02,
                        4.09670671e-02,
                        5.18153700e-15,
                        3.81994693e-14,
                        -3.35841216e-04,
                        1.26309820e-02,
                    ]
                ),
            )
        else:
            # Check objective function value
            np.testing.assert_almost_equal(f[0, 0], 62.40224045726969, decimal=4)

            # detailed cost values
            np.testing.assert_almost_equal(sol.detailed_cost[0]["cost_value_weighted"], 62.40222242578194, decimal=4)
            np.testing.assert_almost_equal(
                sol.detailed_cost[1]["cost_value_weighted"], 1.8031487750452925e-05, decimal=4
            )
            np.testing.assert_almost_equal(
                f[0, 0], sum(sol.detailed_cost[i]["cost_value_weighted"] for i in range(len(sol.detailed_cost)))
            )

            if with_cholesky and with_scaling and use_sx:
                return

            # initial and final position
            np.testing.assert_almost_equal(q[:, 0], np.array([0.34906585, 2.24586773]))
            np.testing.assert_almost_equal(q[:, -1], np.array([0.9256103, 1.29037205]))
            np.testing.assert_almost_equal(qdot[:, 0], np.array([0, 0]))
            np.testing.assert_almost_equal(qdot[:, -1], np.array([0, 0]))

            np.testing.assert_almost_equal(tau[:, 0], np.array([0.42135677, -0.30494447]))
            np.testing.assert_almost_equal(tau[:, -2], np.array([-0.39329968, 0.3615263]))

            np.testing.assert_almost_equal(
                k[:, 0],
                np.array(
                    [0.38339153, 0.16410165, 0.24810509, 0.42872769, -0.35368849, -0.10938936, 0.14249199, -0.25350259]
                ),
            )
            np.testing.assert_almost_equal(ref[:, 0], np.array([2.81907786e-02, 2.84412560e-01, 0, 0]))
            np.testing.assert_almost_equal(
                m[:, 0],
                np.array(
                    [
                        1.11109420e00,
                        -2.00975244e-05,
                        1.52182976e-03,
                        1.80877721e-03,
                        1.76457230e-04,
                        1.11160762e00,
                        -1.58811508e-02,
                        -4.46861689e-02,
                        -1.24668133e-02,
                        -6.45898260e-05,
                        1.12201319e00,
                        5.81308511e-03,
                        -7.64514277e-06,
                        -1.24164397e-02,
                        6.88061131e-04,
                        1.11747957e00,
                    ]
                ),
            )

            np.testing.assert_almost_equal(
                cov[:, -2],
                np.array(
                    [
                        -8.67400623e-03,
                        5.77329567e-05,
                        -1.30885973e-03,
                        1.12501586e-02,
                        4.64929473e-03,
                        2.32462786e-03,
                        4.92631923e-03,
                        3.97615552e-03,
                        6.52664876e-03,
                        -6.66843408e-04,
                    ]
                ),
            )

            np.testing.assert_almost_equal(
                a[:, 3],
                np.array(
                    [
                        1.00000000e00,
                        -8.35886644e-14,
                        -2.60671845e-02,
                        -6.51469362e-02,
                        -1.10663430e-14,
                        1.00000000e00,
                        -3.68704938e-01,
                        7.95318548e-01,
                        -1.00000000e-01,
                        -1.65656031e-14,
                        1.13051096e00,
                        7.33175161e-02,
                        -1.61686165e-14,
                        -1.00000000e-01,
                        6.34380653e-02,
                        9.83897210e-01,
                    ]
                ),
            )

            np.testing.assert_almost_equal(
                c[:, 2],
                np.array(
                    [
                        -1.12917038e-15,
                        4.53652494e-15,
                        -1.35499971e00,
                        1.12950724e00,
                        1.05525107e-14,
                        -2.09358023e-14,
                        1.12950724e00,
                        -3.79903115e00,
                        -2.39923923e-14,
                        4.58953582e-14,
                        -2.78756182e-02,
                        1.26240135e-01,
                        -3.27866630e-14,
                        7.03268708e-14,
                        -9.99367009e-02,
                        2.09729743e-01,
                        -3.14543642e-12,
                        3.70435383e-12,
                        1.91480322e-02,
                        8.03625184e-03,
                        -1.12721323e-12,
                        2.00365744e-12,
                        1.01115604e-03,
                        2.88702060e-03,
                    ]
                ),
            )
