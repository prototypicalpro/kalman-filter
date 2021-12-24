import numpy as np
from matplotlib import pyplot as plt

from applemodel import AppleModel, NormalCameraModel, ConeSensorModel

# state variables: x, x', x'', y, y', y'', z, z', z''
# control input: robot x', x'', y', y'', z', z''
# process noise: constant acceleration model
# sensors: x, y, z
# units are mks
# axis is right hand rule, positive y points towards apple, z=0 centered around apple

def concat_optional(a, *args, **kwargs):
    a = [i for i in a if i is not None]
    return np.concatenate(a, *args, **kwargs)

# project a matrix to n number of state variables
def make_nd(gen, ndim=3):
    def _make_nd(*args, **kwargs):
        mtx = gen(*args, **kwargs)
        base = None
        for i in range(ndim):
            col = None
            for j in range(ndim):
                if i == j:
                    col = concat_optional((col, mtx))
                else:
                    col = concat_optional((col, np.zeros_like(mtx)))
            base = concat_optional((base, col), axis=1)
        return base

    return _make_nd


@make_nd
def get_transition_matrix(delta_t):
    t = delta_t
    return np.array([
        [1, t, 0.5*t*t],
        [0, 1, t],
        [0, 0, 1],
    ])

@make_nd
def get_control_matrix(delta_t):
    t = delta_t
    return np.array([
        [t, 0.5*t*t],
        [1, t],
        [0, 1],
    ])

def get_process_noise(delta_t, accel_std):
    # constant acceleration + discrete noise model
    G = get_control_matrix(delta_t)
    return accel_std**2 * G @ np.transpose(G)

def get_observation_matrix():
    return np.array([
        [1, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0]
    ])

def get_starting_position(initial_pos):
    return np.transpose(np.array([
        initial_pos[0], 0, 0, initial_pos[1], 0, 0, initial_pos[2], 0, 0]))

@make_nd
def get_starting_uncertainty(initial_pos_std):
    i = initial_pos_std**2
    return np.array([
        [i, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ])

if __name__ == '__main__':
    np.seterr(all='raise')

    delta_t_ms = 10
    delta_t = delta_t_ms / 1000
    accel_var = 0.02
    F = get_transition_matrix(delta_t)
    G = get_control_matrix(delta_t)
    Q = get_process_noise(delta_t, accel_var)
    H = get_observation_matrix()
    I = np.eye(H.shape[1], H.shape[1])
    ITERATIONS = 40

    meas_log = []
    est_log = []
    real_log = []
    time_log = []

    x_est = get_starting_position((0, 0, 0.6))
    p_est = get_starting_uncertainty(0.2)

    rng = np.random.default_rng()
    model = AppleModel((0, 0, 0.8), 2, delta_t_ms, NormalCameraModel(0.01, rng), ConeSensorModel(1.2, 0.08, 0.005, rng))

    for _ in range(ITERATIONS):
        control = model.get_control_vector()
        meas, var = model.step()
        
        x_predict = F @ x_est + G @ control
        p_predict = F @ p_est @ np.transpose(F) + Q
        K = p_predict @ np.transpose(H) @ np.linalg.inv(H @ p_predict @ np.transpose(H) + var)
        x_est = x_predict + K @ (meas - H @ x_predict)
        fact = (I - K @ H)
        p_est = fact @ p_predict @ np.transpose(fact) + K @ var @ np.transpose(K)

        est_log.append((x_est, p_est))
        meas_log.append((meas, var))
        real_log.append(model.pos_real)
        time_log.append(model.cur_time)


    real, = plt.plot(time_log, [z for _1, _2, z in real_log])
    est_z, *_ = plt.errorbar(time_log, [est[6] for est, _ in est_log], [np.sqrt(var[5,5]) for meas, var in est_log])
    meas, *_ = plt.errorbar(time_log, [z for (_1, _2, z), _ in meas_log], [np.sqrt(var[2,2]) for meas, var in meas_log])
    plt.legend([real, est_z, meas], ('Real', 'Estimated','Measured'))
    plt.show(block=True)


